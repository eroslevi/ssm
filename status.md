# Project Status

**Last updated:** 2026-06-09
**Current stage:** 3a — Document Loader implementation
**Branch:** claude/ssm-long-document-qa-jgbylw

---

## Completed

- [x] Stage 0: `specs/01_user_spec.md` — APPROVED
  - Two-mode design: `ingest` (once, hours OK) + `check` (per query, seconds)
  - Statement size: few hundred to ~1000 characters
  - Simple local web frontend added (localhost, no cloud)
  - Plain text only, English only, one-sentence violation explanations
- [x] Stage 1: `specs/02_system_spec.md` — APPROVED
  - 5 components: Document Loader, SSM Engine, Compliance Extractor, Output Reporter, Web Frontend
  - Mamba-130M/370M backbone, FastAPI + vanilla HTML, binary checkpoint on disk

---

## In Progress

- [x] Stage 2a: `specs/03_components/01_document_loader.md` — APPROVED
- [x] Stage 2b: `specs/03_components/02_ssm_engine.md` — APPROVED
- [x] Stage 2c: `specs/03_components/03_compliance_extractor.md` — APPROVED
- [x] Stage 2d: `specs/03_components/04_output_reporter.md` — APPROVED
- [x] Stage 2e: `specs/03_components/05_web_frontend.md` — APPROVED
- [ ] Stage 3a: Document Loader — implemented, awaiting eval results from target hardware

---

## Open Questions

None.

---

## Next Action

User runs `python tests/eval_loader.py` on target hardware (Windows/HP EliteBook)
after installing deps (`pip install -r requirements.txt`), shares results here.
