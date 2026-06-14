# Project Status

**Last updated:** 2026-06-14
**Current stage:** 2 — All specs written, awaiting approval
**Branch:** claude/ssm-long-document-qa-jgbylw

---

## Architecture (final — agreed via grilling session 2026-06-14)

Full reset from SSM/Mamba to NLI + LangGraph + knowledge graph architecture.

**Stage 1 (on-prem):** TF-IDF retrieval → mDeBERTa NLI → contradiction score
**Stage 2 (remote):** FAISS retrieval → graph traversal → Azure LLM → citations

See `specs/02_system_spec.md` for full details.

---

## Completed

- [x] Grilling session — all architecture decisions locked (2026-06-14)
- [x] `specs/01_user_spec.md` — rewritten for legal compliance + two-stage check
- [x] `specs/02_system_spec.md` — full rewrite for NLI + LangGraph + graph
- [x] `specs/03_components/01_law_parser.md`
- [x] `specs/03_components/02_index_builder.md`
- [x] `specs/03_components/03_stage1_agent.md`
- [x] `specs/03_components/04_stage2_agent.md`
- [x] `specs/03_components/05_orchestrator.md`
- [x] `specs/03_components/06_reporter.md`
- [x] `specs/03_components/07_web_ui.md`

---

## Awaiting

- [ ] User approval of all specs → then begin Stage 3a: LawParser implementation

---

## Key Decisions (from grilling session)

| Decision | Value |
|---|---|
| Input | Hungarian text, ≤ 2000 chars, web UI |
| Stage 1 model | mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 |
| Stage 2 LLM | Azure AI Foundry, user API key, configurable model (default gpt-4o) |
| NLI threshold | 0.85 default, configurable |
| Stage 1 top-k | 5 |
| Stage 2 seed top-k | 10 |
| Graph hops | 2 default, configurable |
| Graph max articles | 50 |
| Storage | SQLite + FAISS + TF-IDF pkl |
| Embedding model | multilingual-e5-base |
| Agent framework | LangGraph |
| Web framework | FastAPI + vanilla JS + vis.js |
| Graph viz | Subgraph only (articles consulted in current check) |
| Flow | Stage 1 VIOLATION → stop (user can escalate); Stage 1 COMPLIANT → auto Stage 2 |
| Output | Web only, violations list with PTK citations |
| Config | config.yaml |
| Law corpus | Static PTK txt file, re-ingest manually |

---

## Next Action

User reviews all 9 spec files and approves or requests changes.
