from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import faiss
import numpy as np
from openai import AzureOpenAI
from sentence_transformers import SentenceTransformer

from .stage1 import ArticleHit, split_sentences

_EMBED_MODEL      = "intfloat/multilingual-e5-base"
_EMBED_PREFIX_QRY = "query: "
_ARTICLE_TRUNC    = 800   # chars per article sent to LLM

_embed_model: SentenceTransformer | None = None


def _get_embed() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(_EMBED_MODEL)
    return _embed_model


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Stage2Violation:
    sentence: str
    article_ref: str
    article_title: str
    article_excerpt: str
    paragraph_ref: str
    explanation: str


@dataclass
class Subgraph:
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)


@dataclass
class Stage2Result:
    verdict: str
    violations: list[Stage2Violation]
    checked_articles: list[ArticleHit]
    subgraph: Subgraph
    error: str = ""


# ---------------------------------------------------------------------------
# FAISS retriever
# ---------------------------------------------------------------------------

class FAISSRetriever:
    def __init__(self, faiss_path: str, db_path: str) -> None:
        self._index = faiss.read_index(faiss_path)
        self._db    = db_path

    def retrieve(self, sentence: str, top_k: int) -> list[ArticleHit]:
        model = _get_embed()
        vec   = model.encode(
            [_EMBED_PREFIX_QRY + sentence],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype("float32")

        scores, indices = self._index.search(vec, top_k)
        conn = sqlite3.connect(self._db)
        hits: list[ArticleHit] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            row = conn.execute(
                "SELECT id, article_ref, title, full_text FROM articles WHERE faiss_idx = ?",
                (int(idx),),
            ).fetchone()
            if row:
                hits.append(ArticleHit(
                    article_id=row[0],
                    article_ref=row[1],
                    title=row[2],
                    full_text=row[3],
                    tfidf_score=float(score),
                ))
        conn.close()
        return hits


# ---------------------------------------------------------------------------
# Graph traverser
# ---------------------------------------------------------------------------

class GraphTraverser:
    def __init__(self, db_path: str) -> None:
        self._db = db_path

    def expand(
        self,
        seed_ids: list[str],
        hops: int,
        max_articles: int,
    ) -> dict[str, str]:
        """BFS over cross_refs. Returns {article_id: group_label}."""
        result: dict[str, str] = {sid: "seed" for sid in seed_ids}
        frontier = set(seed_ids)
        conn = sqlite3.connect(self._db)

        for hop in range(1, hops + 1):
            if len(result) >= max_articles or not frontier:
                break
            ph  = ",".join("?" * len(frontier))
            rows = conn.execute(
                f"SELECT DISTINCT target_article_id FROM cross_refs "
                f"WHERE source_article_id IN ({ph}) AND target_article_id IS NOT NULL",
                list(frontier),
            ).fetchall()
            new_ids = {r[0] for r in rows} - set(result)
            frontier = set()
            for nid in new_ids:
                if len(result) >= max_articles:
                    break
                result[nid] = f"hop{hop}"
                frontier.add(nid)

        conn.close()
        return result

    def edges_within(self, article_ids: set[str]) -> list[tuple[str, str]]:
        if not article_ids:
            return []
        conn = sqlite3.connect(self._db)
        ph   = ",".join("?" * len(article_ids))
        ids  = list(article_ids)
        rows = conn.execute(
            f"SELECT source_article_id, target_article_id FROM cross_refs "
            f"WHERE source_article_id IN ({ph}) AND target_article_id IN ({ph})",
            ids + ids,
        ).fetchall()
        conn.close()
        return [(r[0], r[1]) for r in rows]


# ---------------------------------------------------------------------------
# Prompt defaults
# ---------------------------------------------------------------------------

_DEFAULT_SYSTEM = (
    "You are a Hungarian legal compliance expert specialising in the Polgári Törvénykönyv "
    "(2013. évi V. törvény). Analyse whether a company statement violates any of the "
    "provided legal provisions. Respond only with a valid JSON object, no markdown."
)

_DEFAULT_USER = """\
Legal provisions from the Polgári Törvénykönyv:

{law_context}

Company statement to check:
{statement}

Does this statement violate any of the above legal provisions?
Return a JSON object:
{{
  "verdict": "VIOLATION" or "COMPLIANT",
  "violations": [
    {{
      "sentence": "exact sentence from the statement that violates the law",
      "article_ref": "e.g. 6:130",
      "paragraph_ref": "e.g. 6:130. § (2) bekezdés",
      "explanation": "one sentence explaining the specific conflict"
    }}
  ],
  "checked_articles": ["6:130", "6:215"]
}}
If compliant, return empty violations array and verdict COMPLIANT.
Always list every article you consulted in checked_articles."""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_stage2(statement: str, config, data_dir: str = "data") -> Stage2Result:
    dp = Path(data_dir)
    retriever = FAISSRetriever(str(dp / "embeddings.faiss"), str(dp / "laws.db"))
    traverser = GraphTraverser(str(dp / "laws.db"))

    sentences = split_sentences(statement)

    # Collect unique seed articles across all sentences
    seed_ids: list[str] = []
    seen: set[str]      = set()
    for sentence in sentences:
        for hit in retriever.retrieve(sentence, config.top_k_stage2):
            if hit.article_id not in seen:
                seed_ids.append(hit.article_id)
                seen.add(hit.article_id)

    # Expand via graph
    groups  = traverser.expand(seed_ids, config.graph_hops, config.graph_max_articles)
    all_ids = set(groups)
    edges   = traverser.edges_within(all_ids)

    # Fetch full texts
    conn     = sqlite3.connect(str(dp / "laws.db"))
    art_info: dict[str, dict] = {}
    for aid in all_ids:
        row = conn.execute(
            "SELECT article_ref, title, full_text FROM articles WHERE id = ?", (aid,)
        ).fetchone()
        if row:
            art_info[aid] = {"ref": row[0], "title": row[1], "text": row[2]}
    conn.close()

    # Build law context string
    law_lines = [
        f"{info['ref']}. § [{info['title']}]\n{info['text'][:_ARTICLE_TRUNC]}"
        for aid, info in art_info.items()
    ]
    law_context = "\n\n---\n\n".join(law_lines)

    # Call Azure LLM
    sys_prompt  = config.stage2_system_prompt or _DEFAULT_SYSTEM
    user_tmpl   = config.stage2_user_prompt   or _DEFAULT_USER
    user_prompt = user_tmpl.format(law_context=law_context, statement=statement)

    try:
        client = AzureOpenAI(
            azure_endpoint=config.azure_endpoint,
            api_key=config.azure_api_key,
            api_version="2024-02-01",
        )
        resp = client.chat.completions.create(
            model=config.azure_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            timeout=25.0,
        )
        data = json.loads(resp.choices[0].message.content)
    except Exception as exc:
        return Stage2Result(
            verdict="COMPLIANT",
            violations=[],
            checked_articles=[],
            subgraph=Subgraph(),
            error=str(exc),
        )

    # Parse LLM response
    def _find_id(ref: str) -> str:
        for aid, info in art_info.items():
            if info["ref"] == ref:
                return aid
        return ""

    violations = [
        Stage2Violation(
            sentence=v.get("sentence", ""),
            article_ref=v.get("article_ref", ""),
            article_title=art_info.get(_find_id(v.get("article_ref", "")), {}).get("title", ""),
            article_excerpt=art_info.get(_find_id(v.get("article_ref", "")), {}).get("text", "")[:300],
            paragraph_ref=v.get("paragraph_ref", ""),
            explanation=v.get("explanation", ""),
        )
        for v in data.get("violations", [])
    ]

    checked = [
        ArticleHit(
            article_id=_find_id(ref),
            article_ref=ref,
            title=art_info.get(_find_id(ref), {}).get("title", ""),
            full_text="",
            tfidf_score=0.0,
        )
        for ref in data.get("checked_articles", [])
    ]

    subgraph = Subgraph(
        nodes=[
            {
                "id":    aid,
                "label": info["ref"],
                "title": info["title"],
                "group": groups[aid],
            }
            for aid, info in art_info.items()
        ],
        edges=[{"from": s, "to": t} for s, t in edges],
    )

    return Stage2Result(
        verdict=data.get("verdict", "COMPLIANT"),
        violations=violations,
        checked_articles=checked,
        subgraph=subgraph,
    )
