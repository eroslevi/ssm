"""
Stage 3b evaluation — IndexBuilder acceptance criteria.

Run from repo root:
    python tests/eval_indexer.py

Builds index from the full PTK into data/ directory.
"""
import sys
import sqlite3
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ptk_check.parser  import parse_ptk
from ptk_check.indexer import build_index

PTK_FILE = "/root/.claude/uploads/4dc6d9a0-3817-5762-86a7-fb7407f6e457/a4f4df3c-ptk.txt"
DATA_DIR = "data"


def _r(label, passed, detail=""):
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}" + (f": {detail}" if detail else ""))


def main():
    print("Parsing PTK...")
    articles = parse_ptk(PTK_FILE)
    print(f"  {len(articles)} articles parsed")

    print(f"\nBuilding index into {DATA_DIR}/ ...")
    t0 = time.time()
    build_index(articles, data_dir=DATA_DIR)
    elapsed = time.time() - t0
    print(f"  built in {elapsed:.1f}s\n")

    print("Running acceptance criteria:")

    db   = Path(DATA_DIR) / "laws.db"
    tpkl = Path(DATA_DIR) / "tfidf.pkl"
    fais = Path(DATA_DIR) / "embeddings.faiss"

    _r("AC1 all 3 artifacts created",
       db.exists() and tpkl.exists() and fais.exists(),
       f"db={db.stat().st_size//1024}KB tfidf={tpkl.stat().st_size//1024}KB faiss={fais.stat().st_size//1024}KB")

    conn = sqlite3.connect(db)
    n_art   = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    n_xref  = conn.execute("SELECT COUNT(*) FROM cross_refs").fetchone()[0]
    n_no_fi = conn.execute("SELECT COUNT(*) FROM articles WHERE faiss_idx IS NULL").fetchone()[0]
    conn.close()

    _r("AC2 article count matches", n_art == len(articles), f"db={n_art} parsed={len(articles)}")
    _r("AC3 cross-refs stored", n_xref >= 200, f"{n_xref} cross-refs")
    _r("AC5 faiss_idx populated", n_no_fi == 0, f"{n_no_fi} articles without faiss_idx")

    import joblib
    import numpy as np
    saved = joblib.load(tpkl)
    vec = saved["vectorizer"].transform(["szerződés"])
    scores = (saved["matrix"] @ vec.T).toarray().flatten()
    top_id = saved["article_ids"][scores.argmax()]
    _r("AC6 TF-IDF query returns results", scores.max() > 0, f"top article: {top_id}")

    import faiss as F
    from sentence_transformers import SentenceTransformer
    index = F.read_index(str(fais))
    _r("AC4 FAISS index size matches", index.ntotal == len(articles),
       f"faiss={index.ntotal} articles={len(articles)}")

    _r("AC8 ingest time", elapsed < 600, f"{elapsed:.1f}s (limit 600s)")

    print("\nDone. Share results for Stage 3b review gate.")


if __name__ == "__main__":
    main()
