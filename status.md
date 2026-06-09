# Project Status

**Last updated:** 2026-06-09
**Current stage:** 0 — User Spec (revised, awaiting approval)
**Branch:** claude/ssm-long-document-qa-jgbylw

---

## Completed

- [x] Concept discussion and use case selection
  - Input stream: [law corpus | company statement] concatenated
  - Single-pass SSM, very low volatility, no retrieval
  - Violations detected when statement contradicts accumulated law context
- [x] Environment setup (CLAUDE.md, directory structure)
- [x] Stage 0 first draft — revised after review:
  - Statement size corrected: few hundred to ~1000 characters
  - Two-mode architecture confirmed: `ingest` (once, hours OK) + `check` (per query, seconds)

---

## In Progress

- [ ] Stage 0: `specs/01_user_spec.md` revised — awaiting human approval

---

## Open Questions

None.

---

## Next Action

Await human approval of `specs/01_user_spec.md`, then begin Stage 1 (system spec).
