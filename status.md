# Project Status

**Last updated:** 2026-06-14
**Current stage:** 3a — LawParser evaluation
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

- [ ] Stage 3a: LawParser — awaiting eval results

---

## Next Actions (in order)

1. `pip install -r requirements.txt`
2. `python tests/eval_parser.py` → share output for Stage 3a review
3. `python tests/eval_indexer.py` → share output for Stage 3b review
4. `python tests/eval_stage1.py` → share output for Stage 3c review
5. Configure `config.yaml` with Azure credentials → test Stage 2
6. `python -m ptk_check serve` → test web UI
