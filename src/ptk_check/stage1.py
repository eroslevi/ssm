from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import joblib
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

_NLI_MODEL   = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
_MIN_WORDS   = 3
_MAX_PREMISE = 1500  # chars fed to NLI as premise


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ArticleHit:
    article_id: str
    article_ref: str
    title: str
    full_text: str
    tfidf_score: float


@dataclass
class NLIScore:
    entailment: float
    neutral: float
    contradiction: float


@dataclass
class Stage1Violation:
    sentence: str
    article_ref: str
    article_title: str
    article_excerpt: str
    contradiction_score: float


@dataclass
class Stage1Result:
    verdict: str           # "VIOLATION" | "COMPLIANT"
    violations: list[Stage1Violation]
    checked_articles: list[ArticleHit]


# ---------------------------------------------------------------------------
# TF-IDF retriever
# ---------------------------------------------------------------------------

class TFIDFRetriever:
    def __init__(self, tfidf_path: str, db_path: str) -> None:
        saved = joblib.load(tfidf_path)
        self.vectorizer  = saved["vectorizer"]
        self.matrix      = saved["matrix"]
        self.article_ids = saved["article_ids"]
        self._db         = db_path

    def retrieve(self, sentence: str, top_k: int) -> list[ArticleHit]:
        vec    = self.vectorizer.transform([sentence])
        scores = (self.matrix @ vec.T).toarray().flatten()
        top_idx = scores.argsort()[-top_k:][::-1]

        conn = sqlite3.connect(self._db)
        hits: list[ArticleHit] = []
        for idx in top_idx:
            if scores[idx] == 0:
                continue
            aid = self.article_ids[idx]
            row = conn.execute(
                "SELECT article_ref, title, full_text FROM articles WHERE id = ?", (aid,)
            ).fetchone()
            if row:
                hits.append(ArticleHit(
                    article_id=aid,
                    article_ref=row[0],
                    title=row[1],
                    full_text=row[2],
                    tfidf_score=float(scores[idx]),
                ))
        conn.close()
        return hits


# ---------------------------------------------------------------------------
# NLI scorer — lazy-loaded singleton
# ---------------------------------------------------------------------------

class _NLIScorer:
    def __init__(self) -> None:
        self._tokenizer = None
        self._model     = None
        self._label_map: dict[int, str] = {}

    def _load(self) -> None:
        if self._model is not None:
            return
        self._tokenizer = AutoTokenizer.from_pretrained(_NLI_MODEL)
        self._model     = AutoModelForSequenceClassification.from_pretrained(_NLI_MODEL)
        self._model.eval()
        self._label_map = {v: k for k, v in self._model.config.label2id.items()}

    def score_batch(self, pairs: list[tuple[str, str]]) -> list[NLIScore]:
        """Score a batch of (premise, hypothesis) pairs in one forward pass."""
        self._load()
        premises    = [p[:_MAX_PREMISE] for p, _ in pairs]
        hypotheses  = [h for _, h in pairs]
        inputs = self._tokenizer(
            premises,
            hypotheses,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        with torch.no_grad():
            logits = self._model(**inputs).logits
        probs_batch = torch.softmax(logits, dim=-1)

        results = []
        for probs in probs_batch:
            s: dict[str, float] = {}
            for idx, prob in enumerate(probs):
                s[self._label_map.get(idx, "").upper()] = float(prob)
            results.append(NLIScore(
                entailment=s.get("ENTAILMENT", 0.0),
                neutral=s.get("NEUTRAL", 0.0),
                contradiction=s.get("CONTRADICTION", 0.0),
            ))
        return results


_scorer = _NLIScorer()


# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.split()) >= _MIN_WORDS]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_stage1(statement: str, config, data_dir: str = "data") -> Stage1Result:
    dp = Path(data_dir)
    retriever = TFIDFRetriever(str(dp / "tfidf.pkl"), str(dp / "laws.db"))

    sentences  = split_sentences(statement)
    violations: list[Stage1Violation] = []
    all_hits:   list[ArticleHit]      = []
    seen_aids:  set[str]              = set()

    for sentence in sentences:
        hits = retriever.retrieve(sentence, config.top_k_stage1)
        for hit in hits:
            if hit.article_id not in seen_aids:
                seen_aids.add(hit.article_id)
                all_hits.append(hit)

        if not hits:
            continue
        nli_scores = _scorer.score_batch([(h.full_text, sentence) for h in hits])
        for hit, nli in zip(hits, nli_scores):
            if nli.contradiction >= config.nli_threshold:
                violations.append(Stage1Violation(
                    sentence=sentence,
                    article_ref=hit.article_ref,
                    article_title=hit.title,
                    article_excerpt=hit.full_text[:300],
                    contradiction_score=nli.contradiction,
                ))

    return Stage1Result(
        verdict="VIOLATION" if violations else "COMPLIANT",
        violations=violations,
        checked_articles=all_hits,
    )
