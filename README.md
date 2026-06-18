# PTK Compliance Checker

Checks company statements for compliance with the Hungarian Civil Code
(Polgári Törvénykönyv — 2013. évi V. törvény).

Uses a two-stage pipeline:

- **Stage 1 (on-premises):** TF-IDF keyword retrieval + mDeBERTa NLI contradiction
  detection. Fast, runs fully offline.
- **Stage 2 (Azure):** FAISS semantic retrieval + knowledge graph traversal +
  GPT-class LLM reasoning with PTK citations. Triggered automatically on
  COMPLIANT results, or manually by the user on VIOLATION results.

---

## Requirements

- Python 3.10 or later
- Windows (tested), Linux/macOS should work
- ~2 GB disk for model weights (downloaded automatically on first run)
- Azure AI Foundry deployment for Stage 2 (Stage 1 works without it)

---

## Installation

```bat
git clone <repo-url>
cd ssm
pip install -r requirements.txt
```

No further installation is required. Use `start.bat` to run the tool.

---

## First-time setup — ingest the PTK

Before the tool can check any statement, it needs to parse and index the PTK text file.
Obtain the plain-text version of the 2013. évi V. törvény and run:

```bat
start.bat ingest --file path\to\ptk.txt
```

This creates three files in the `data\` directory:

| File | Contents | Size |
|---|---|---|
| `data\laws.db` | SQLite — all 1586 articles, paragraphs, cross-references | ~4 MB |
| `data\tfidf.pkl` | TF-IDF sparse index for Stage 1 keyword search | ~1.5 MB |
| `data\embeddings.faiss` | FAISS dense index for Stage 2 semantic search | ~4.7 MB |

Ingestion downloads the `intfloat/multilingual-e5-base` model (~500 MB) on first run
and takes around 8 minutes on CPU.

---

## Azure credentials (Stage 2 only)

Stage 2 requires an Azure AI Foundry deployment. Set these environment variables
before starting the server:

```bat
set AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
set AZURE_OPENAI_API_KEY=your-key
set AZURE_OPENAI_DEPLOYMENT=your-deployment-name
set AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

Stage 1 works without these — the tool will return an error only if Stage 2 is triggered
without credentials.

---

## Starting the web UI

```bat
start.bat serve
```

The browser opens automatically once the server is ready at `http://127.0.0.1:8000`.

On first use the mDeBERTa NLI model (~600 MB) is downloaded and cached. Subsequent
starts are faster.

To use a different port:

```bat
start.bat serve --port 8080
```

---

## Using the tool

### Check a statement

1. Type or paste a company statement (Hungarian) into the text area. Maximum 2000 characters.
2. Click **Check compliance**.
3. Stage 1 runs on-premises. Results appear in the left panel within 1–2 minutes (CPU).

### Interpreting Stage 1 results

| Verdict | Meaning |
|---|---|
| **VIOLATION** | At least one sentence contradicts a PTK article with ≥ 85% confidence. The flagged sentence, article reference, and contradiction score are shown. |
| **COMPLIANT** | No high-confidence contradiction found. Stage 2 is triggered automatically to confirm. |

### Stage 2 deep analysis

Stage 2 starts automatically after a COMPLIANT Stage 1 result.
After a VIOLATION result, click **Run deep analysis** to escalate manually.

Stage 2 results appear in the right panel and include:

- Final verdict (VIOLATION or COMPLIANT)
- Per-sentence violation explanations with precise PTK citations (e.g. `6:130. § (2) bekezdés`)
- A knowledge subgraph showing which articles were consulted and how they are related

### Subgraph node colours

| Colour | Meaning |
|---|---|
| Blue | Seed articles (directly retrieved by FAISS) |
| Green | 1-hop neighbours (followed via cross-references) |
| Grey | 2-hop neighbours |
| Red | Articles cited in a violation |

---

## How the search works

### Stage 1

The statement is split into sentences. For each sentence:

1. **TF-IDF retrieval** — the top 5 PTK articles by keyword overlap are fetched from
   the on-disk index (`tfidf.pkl` loaded into RAM).
2. **NLI scoring** — all 5 (article, sentence) pairs are scored in one batched forward
   pass through `mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`. If any contradiction
   probability ≥ 0.85, a violation is recorded.

No cross-references are followed in Stage 1.

### Stage 2

1. **FAISS semantic retrieval** — the top 10 articles by semantic similarity are found
   using dense embeddings (multilingual-e5-base, dim 768).
2. **Graph traversal** — BFS over the cross-reference table, up to 2 hops, capped at
   50 articles total.
3. **LLM reasoning** — all retrieved articles (truncated to 800 chars each) are sent
   to the Azure LLM in a single prompt. The model returns a structured JSON verdict
   with per-sentence citations.

---

## Re-ingesting after a PTK update

Simply run the ingest command again with the new file. The existing `data\` directory
is overwritten.

```bat
start.bat ingest --file path\to\new-ptk.txt
```

---

## Tuning (config.yaml)

| Parameter | Default | Effect |
|---|---|---|
| `nli_threshold` | `0.85` | Minimum contradiction score to flag a violation in Stage 1. Higher = fewer false positives, more false negatives. |
| `top_k_stage1` | `5` | Articles retrieved per sentence in Stage 1. |
| `top_k_stage2` | `10` | Seed articles retrieved by FAISS in Stage 2. |
| `graph_hops` | `2` | BFS depth for cross-reference traversal in Stage 2. |
| `graph_max_articles` | `50` | Maximum articles passed to the LLM in Stage 2. |
| `azure_model` | `gpt-4o` | Azure deployment name (overridden by `AZURE_OPENAI_DEPLOYMENT`). |
