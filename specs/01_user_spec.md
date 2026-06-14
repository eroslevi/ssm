# User Specification — Hungarian Legal Compliance Checker

**Stage:** 0 | **Status:** APPROVED

---

## Purpose

A local tool that checks whether a Hungarian company statement complies with the
Polgári Törvénykönyv (2013. évi V. törvény — Civil Code). The tool runs on-premises
for the fast first-pass check and calls a remote Azure-hosted LLM for deep analysis.

---

## Users

Compliance officers, lawyers, or multi-agent pipelines that need to verify whether
a company statement (a few sentences to one paragraph) conflicts with Hungarian civil law.

---

## Two-Mode Architecture

| Mode | Command | When to run |
|------|---------|-------------|
| `ingest` | `python -m ptk_check ingest --file ptk.txt` | Once, when the law file is updated |
| `serve` | `python -m ptk_check serve` | Start the web UI |

`ingest` parses the PTK text file and builds the retrieval indexes (SQLite, TF-IDF, FAISS).
`serve` starts a local FastAPI web server; the user opens `http://localhost:8000`.

---

## Inputs

| Field | Format | Constraint |
|-------|--------|------------|
| Law corpus | Plain text `.txt` (PTK as provided) | One-time ingest |
| Statement to check | Plain Hungarian text, pasted in web UI | ≤ 2,000 characters |

---

## Two-Stage Check

### Stage 1 — Fast on-prem check (always runs)
- TF-IDF retrieves top-5 PTK articles most similar to each statement sentence
- NLI model checks each (article, sentence) pair for contradiction
- If contradiction score ≥ threshold (default 0.85): **NON-COMPLIANT** — stop
- If no high-confidence contradiction: **proceed to Stage 2**

### Stage 2 — Deep remote analysis (auto after Stage 1 COMPLIANT; manual after Stage 1 VIOLATION)
- FAISS retrieves top-10 semantically similar articles
- Graph traversal follows cross-references (2 hops, ≤ 50 articles)
- Azure-hosted LLM reasons over the full legal subgraph
- Returns **COMPLIANT** or **NON-COMPLIANT** with PTK citations

---

## Output

Both stages produce the same structure:

**If NON-COMPLIANT:**
1. Verdict banner: NON-COMPLIANT
2. Per violation:
   - Offending sentence from the statement
   - PTK citation: `6:130. §` + article title
   - Relevant article text excerpt
   - One-sentence explanation of the conflict
3. "Run deep analysis" button (Stage 1 result only)

**If COMPLIANT:**
1. Verdict banner: COMPLIANT
2. List of PTK articles consulted and found consistent

---

## Performance Expectations

| Mode | Expected duration |
|------|-------------------|
| `ingest` | Minutes (one-time) |
| Stage 1 check | < 5 seconds |
| Stage 2 check | < 30 seconds |

---

## Constraints

- Windows 10/11, HP EliteBook (16 GB RAM, no dedicated GPU assumed)
- CPU execution; CUDA optional
- No cloud calls except Stage 2 Azure LLM
- Python 3.10+, `pip install` only
- No authentication required (localhost only)
- English UI, Hungarian law text and statements
