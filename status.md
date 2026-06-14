# Project Status

**Last updated:** 2026-06-14
**Current stage:** 3d — end-to-end integration & web UI
**Branch:** claude/ssm-long-document-qa-jgbylw

---

## Architecture

Two-stage Hungarian legal compliance checker:
- **Stage 1 (on-prem):** TF-IDF retrieval → mDeBERTa NLI → contradiction score
- **Stage 2 (remote):** FAISS + graph traversal → Azure LLM → PTK citations
- **Framework:** LangGraph
- **Storage:** SQLite + FAISS + TF-IDF pkl

---

## Completed

- [x] All specs approved (2026-06-14)
- [x] Full implementation committed
- [x] Stage 3a: LawParser — PASSED (1586 articles, all 8 books, AC1–AC6 green, 2026-06-14)
- [x] Stage 3b: IndexBuilder — PASSED (db=3820KB, faiss=1586 vectors, 9579 cross-refs, 456s, AC1–AC8 green, 2026-06-14)
- [x] Stage 3c: Stage1Agent — PASSED (0 compliant violations, 6 non-compliant violations incl. 6:124@0.992 + 6:62@0.914, AC1–AC6 green, 2026-06-14)

---

## Implementation checklist

| File | Status |
|---|---|
| `src/ptk_check/config.py` | ✓ |
| `src/ptk_check/parser.py` | ✓ |
| `src/ptk_check/indexer.py` | ✓ |
| `src/ptk_check/stage1.py` | ✓ |
| `src/ptk_check/stage2.py` | ✓ |
| `src/ptk_check/orchestrator.py` | ✓ |
| `src/ptk_check/reporter.py` | ✓ |
| `src/ptk_check/web/server.py` | ✓ |
| `src/ptk_check/web/index.html` | ✓ |
| `src/ptk_check/__main__.py` | ✓ |
| `config.yaml` | ✓ |
| `requirements.txt` | ✓ |
| `tests/eval_parser.py` | ✓ |
| `tests/eval_indexer.py` | ✓ |
| `tests/eval_stage1.py` | ✓ |

---

## In Progress

- [ ] Stage 3d: end-to-end integration — Azure credentials + web UI

---

## Next Actions (in order)

1. Fill in `config.yaml` with your Azure AI Foundry endpoint, API key, and model name
2. `python -m ptk_check serve` → opens browser at http://127.0.0.1:8000
3. Paste a test statement → verify Stage 1 runs, escalate to Stage 2, check graph visualization
