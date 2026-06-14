# System Specification — Hungarian Legal Compliance Checker

**Stage:** 1 | **Status:** APPROVED

---

## System Overview

```
ingest mode:
  ptk.txt → [LawParser] → [IndexBuilder] → laws.db + tfidf.pkl + embeddings.faiss

serve mode:
  browser → FastAPI → [Orchestrator (LangGraph)]
                          ├─ [Stage1Agent] → TFIDFRetriever + NLIScorer
                          └─ [Stage2Agent] → FAISSRetriever + GraphTraverser + AzureLLM
                      → [Reporter] → web UI (verdict + citations + subgraph)
```

---

## Components

### 1. LawParser
Parses the PTK plain text file into structured articles.
- Extracts hierarchy: Book → Part → Title/Chapter → Article → Paragraph → Sub-point
- Extracts cross-references from article body text (`X:Y. §` pattern)
- Outputs a list of structured article dicts

### 2. IndexBuilder
Builds the three retrieval artifacts from parsed articles:
- **SQLite** (`laws.db`): articles, paragraphs, cross-reference edges
- **TF-IDF** (`tfidf.pkl`): sklearn vectorizer + sparse matrix for Stage 1 retrieval
- **FAISS** (`embeddings.faiss`): dense article vectors via `multilingual-e5-base` for Stage 2

### 3. Stage1Agent (LangGraph node — on-prem)
Tools: `TFIDFRetriever`, `NLIScorer`
- Splits statement into sentences
- Retrieves top-5 PTK articles per sentence via TF-IDF
- Scores each (article, sentence) pair with `mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`
- Returns VIOLATION if any pair scores ≥ threshold (default 0.85), else COMPLIANT

### 4. Stage2Agent (LangGraph node — remote)
Tools: `FAISSRetriever`, `GraphTraverser`, `AzureLLM`
- Retrieves top-10 seed articles per sentence via FAISS
- Expands via graph traversal (default 2 hops, ≤ 50 articles total)
- Calls Azure AI Foundry LLM with full article texts + statement
- Returns COMPLIANT or NON-COMPLIANT with PTK citations and explanation

### 5. Orchestrator
LangGraph state graph managing the two-stage pipeline:
- Stage1Node → ConditionalEdge → Stage2Node or END
- Routing: VIOLATION (≥ threshold) → END; COMPLIANT → Stage2Node
- Manual escalation: user-triggered re-run through Stage2Node
- All parameters from `config.yaml`

### 6. Reporter
Formats pipeline output for the web UI:
- Verdict banner, violation list, PTK citations
- COMPLIANT: list of articles checked and found consistent
- Subgraph JSON for vis.js visualization

### 7. Web UI
FastAPI + single HTML page (`index.html`):
- Statement text area (≤ 2,000 chars), submit button
- Results panel: Stage 1 result + optional Stage 2 result side by side
- "Run deep analysis" button (visible after Stage 1 VIOLATION)
- vis.js subgraph showing consulted articles and cross-reference edges

---

## Data Store

```
data/
  laws.db            ← SQLite: laws, articles, paragraphs, cross_refs tables
  tfidf.pkl          ← sklearn TF-IDF vectorizer + sparse matrix + article_id list
  embeddings.faiss   ← FAISS flat index (L2), vectors in faiss_idx order
```

---

## Configuration

```yaml
# config.yaml
nli_threshold: 0.85
top_k_stage1: 5
top_k_stage2: 10
graph_hops: 2
graph_max_articles: 50
azure_endpoint: "https://..."
azure_api_key: "..."
azure_model: "gpt-4o"
stage2_system_prompt: |
  You are a Hungarian legal compliance expert...
stage2_user_prompt: |
  Law provisions:\n{law_context}\n\nStatement:\n{statement}\n\n...
```

---

## Technology Stack

| Concern | Choice |
|---------|--------|
| Agent framework | LangGraph |
| Stage 1 NLI model | mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 (~600 MB) |
| Stage 2 embedding model | multilingual-e5-base (~560 MB) |
| Stage 2 LLM | Azure AI Foundry (OpenAI-compatible API) |
| Vector index | FAISS (faiss-cpu) |
| Relational store | SQLite (stdlib) |
| TF-IDF | scikit-learn |
| Web server | FastAPI + uvicorn |
| Graph visualization | vis.js (CDN) |

---

## File Layout

```
ptk_check/
├── CLAUDE.md
├── status.md
├── config.yaml
├── requirements.txt
├── specs/
│   ├── 01_user_spec.md
│   ├── 02_system_spec.md
│   └── 03_components/
├── data/                        ← created by ingest
│   ├── laws.db
│   ├── tfidf.pkl
│   └── embeddings.faiss
├── src/
│   └── ptk_check/
│       ├── __init__.py
│       ├── __main__.py          ← CLI entry point
│       ├── parser.py            ← LawParser
│       ├── indexer.py           ← IndexBuilder
│       ├── stage1.py            ← Stage1Agent + tools
│       ├── stage2.py            ← Stage2Agent + tools
│       ├── orchestrator.py      ← LangGraph graph
│       ├── reporter.py          ← Reporter
│       ├── config.py            ← config.yaml loader
│       └── web/
│           ├── server.py        ← FastAPI app
│           └── index.html
└── tests/
    ├── fixtures/
    │   ├── ptk_sample.txt       ← first 50 articles of PTK for testing
    │   └── statements/
    │       ├── compliant.txt
    │       └── non_compliant.txt
    └── eval_*.py
```
