# Component Spec — IndexBuilder

**Stage:** 2b | **Status:** APPROVED

---

## Responsibility

Takes the list of `ParsedArticle` objects from LawParser and builds three
retrieval artifacts saved to the `data/` directory.

---

## Outputs

### 1. `data/laws.db` — SQLite database

```sql
CREATE TABLE laws (
    law_id TEXT PRIMARY KEY, title TEXT, short_name TEXT,
    source_file TEXT, ingested_at TEXT
);
CREATE TABLE articles (
    id TEXT PRIMARY KEY,        -- "2013-5/6:130"
    law_id TEXT, article_ref TEXT, book_num INTEGER, article_num INTEGER,
    title TEXT, full_text TEXT, book_name TEXT, part_name TEXT,
    title_name TEXT, chapter_name TEXT, faiss_idx INTEGER,
    FOREIGN KEY (law_id) REFERENCES laws(law_id)
);
CREATE TABLE paragraphs (
    id TEXT PRIMARY KEY,        -- "2013-5/6:130/2"
    article_id TEXT, para_num INTEGER, point_label TEXT, text TEXT,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
CREATE TABLE cross_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_article_id TEXT, target_article_id TEXT,
    target_ref TEXT, context TEXT
);
CREATE INDEX idx_crossrefs_source ON cross_refs(source_article_id);
CREATE INDEX idx_crossrefs_target ON cross_refs(target_article_id);
```

### 2. `data/tfidf.pkl` — sklearn TF-IDF
```python
{"vectorizer": TfidfVectorizer, "matrix": csr_matrix, "article_ids": list[str]}
```
- `max_features=100_000`, `sublinear_tf=True`
- One row per article, rows correspond to `article_ids` list

### 3. `data/embeddings.faiss` — FAISS flat index
- Model: `intfloat/multilingual-e5-base` (768-dim vectors)
- Index type: `IndexFlatIP` (inner product, vectors L2-normalised → cosine similarity)
- `faiss_idx` column in SQLite `articles` table maps vector position → article

---

## Build Process

1. Insert law metadata into `laws` table
2. For each article: insert into `articles` and `paragraphs` tables
3. Insert cross-reference edges (skip if target not in DB)
4. Fit TF-IDF on all `full_text` values → save `tfidf.pkl`
5. Embed all articles with `multilingual-e5-base` → save `embeddings.faiss`
6. Update `faiss_idx` column in `articles` table

---

## Acceptance Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| AC1 | All 3 artifacts created | files exist and size > 0 |
| AC2 | Article count matches parser | `SELECT COUNT(*) FROM articles` == `len(parsed)` |
| AC3 | Cross-refs stored | `SELECT COUNT(*) FROM cross_refs` ≥ 200 |
| AC4 | FAISS index size matches | `index.ntotal` == `len(articles)` |
| AC5 | faiss_idx populated | no NULL `faiss_idx` in articles table |
| AC6 | TF-IDF query returns results | `vectorizer.transform(["szerződés"])` → top result is relevant |
| AC7 | FAISS query returns results | nearest neighbour of `"kártérítés"` embedding is a tort article |
| AC8 | Ingest time | completes in < 10 minutes on target hardware |
