# Project Status

**Last updated:** 2026-06-14
**Current stage:** 3c — Stage1Agent evaluation
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

- [ ] Stage 3c: Stage1Agent — awaiting eval results

---

## Next Actions (in order)

1. `python tests/eval_stage1.py` → share output for Stage 3c review (downloads mDeBERTa ~600 MB on first run)
2. Configure `config.yaml` with Azure credentials → test Stage 2
3. `python -m ptk_check serve` → test web UI
