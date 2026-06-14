from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import faiss
import joblib
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

from .parser import ParsedArticle

_EMBED_MODEL = "intfloat/multilingual-e5-base"
_EMBED_PREFIX_DOC = "passage: "


def build_index(
    articles: list[ParsedArticle],
    law_id: str = "2013-5",
    law_title: str = "2013. évi V. törvény a Polgári Törvénykönyvről",
    data_dir: str = "data",
) -> None:
    data_path = Path(data_dir)
    data_path.mkdir(exist_ok=True)

    db_path    = data_path / "laws.db"
    tfidf_path = data_path / "tfidf.pkl"
    faiss_path = data_path / "embeddings.faiss"

    print(f"  [{len(articles)} articles] building SQLite...")
    _build_sqlite(articles, law_id, law_title, db_path)

    print("  building TF-IDF index...")
    _build_tfidf(articles, tfidf_path)

    print("  embedding articles (multilingual-e5-base)...")
    _build_faiss(articles, faiss_path, db_path)

    print(f"  done → {data_dir}/")


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS laws (
    law_id TEXT PRIMARY KEY,
    title TEXT,
    short_name TEXT,
    source_file TEXT,
    ingested_at TEXT
);
CREATE TABLE IF NOT EXISTS articles (
    id           TEXT PRIMARY KEY,
    law_id       TEXT NOT NULL,
    article_ref  TEXT NOT NULL,
    book_num     INTEGER NOT NULL,
    article_num  INTEGER NOT NULL,
    title        TEXT,
    full_text    TEXT NOT NULL,
    book_name    TEXT,
    part_name    TEXT,
    title_name   TEXT,
    chapter_name TEXT,
    faiss_idx    INTEGER,
    FOREIGN KEY (law_id) REFERENCES laws(law_id)
);
CREATE TABLE IF NOT EXISTS paragraphs (
    id          TEXT PRIMARY KEY,
    article_id  TEXT NOT NULL,
    para_num    INTEGER,
    point_label TEXT,
    text        TEXT NOT NULL,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
CREATE TABLE IF NOT EXISTS cross_refs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_article_id   TEXT NOT NULL,
    target_article_id   TEXT,
    target_ref          TEXT NOT NULL,
    context             TEXT
);
CREATE INDEX IF NOT EXISTS idx_xref_src ON cross_refs(source_article_id);
CREATE INDEX IF NOT EXISTS idx_xref_tgt ON cross_refs(target_article_id);
CREATE INDEX IF NOT EXISTS idx_art_law  ON articles(law_id);
CREATE INDEX IF NOT EXISTS idx_art_ref  ON articles(law_id, article_ref);
"""


def _build_sqlite(
    articles: list[ParsedArticle],
    law_id: str,
    law_title: str,
    db_path: Path,
) -> None:
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)

    conn.execute(
        "INSERT OR REPLACE INTO laws VALUES (?,?,?,?,?)",
        (law_id, law_title, "Ptk.", "", datetime.now().isoformat()),
    )

    ref_to_id = {a.article_ref: f"{a.law_id}/{a.article_ref}" for a in articles}

    for a in articles:
        article_id = f"{a.law_id}/{a.article_ref}"
        conn.execute(
            "INSERT OR REPLACE INTO articles VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                article_id, a.law_id, a.article_ref,
                a.book_num, a.article_num, a.title, a.full_text,
                a.book_name, a.part_name, a.title_name, a.chapter_name,
                None,  # faiss_idx set later
            ),
        )

        for p in a.paragraphs:
            para_id = f"{article_id}/{p['num']}"
            conn.execute(
                "INSERT OR REPLACE INTO paragraphs VALUES (?,?,?,?,?)",
                (para_id, article_id, p["num"], None, p["text"]),
            )
            for pt in p.get("points", []):
                pt_id = f"{para_id}/{pt['label']}"
                conn.execute(
                    "INSERT OR REPLACE INTO paragraphs VALUES (?,?,?,?,?)",
                    (pt_id, article_id, p["num"], pt["label"], pt["text"]),
                )

        for ref in a.cross_refs:
            conn.execute(
                "INSERT INTO cross_refs (source_article_id, target_article_id, target_ref) VALUES (?,?,?)",
                (article_id, ref_to_id.get(ref), ref),
            )

    conn.commit()
    conn.close()
    print(f"    SQLite: {db_path} ({db_path.stat().st_size // 1024} KB)")


# ---------------------------------------------------------------------------
# TF-IDF
# ---------------------------------------------------------------------------

def _build_tfidf(articles: list[ParsedArticle], tfidf_path: Path) -> None:
    texts       = [a.full_text for a in articles]
    article_ids = [f"{a.law_id}/{a.article_ref}" for a in articles]

    vectorizer = TfidfVectorizer(max_features=100_000, sublinear_tf=True)
    matrix     = vectorizer.fit_transform(texts)

    joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "article_ids": article_ids}, tfidf_path)
    print(f"    TF-IDF: {matrix.shape[0]} docs × {matrix.shape[1]} features")


# ---------------------------------------------------------------------------
# FAISS
# ---------------------------------------------------------------------------

def _build_faiss(articles: list[ParsedArticle], faiss_path: Path, db_path: Path) -> None:
    model = SentenceTransformer(_EMBED_MODEL)
    texts = [_EMBED_PREFIX_DOC + a.full_text[:1000] for a in articles]
    article_ids = [f"{a.law_id}/{a.article_ref}" for a in articles]

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    faiss.write_index(index, str(faiss_path))

    conn = sqlite3.connect(db_path)
    for i, aid in enumerate(article_ids):
        conn.execute("UPDATE articles SET faiss_idx = ? WHERE id = ?", (i, aid))
    conn.commit()
    conn.close()

    print(f"    FAISS: {index.ntotal} vectors, dim={dim}")
