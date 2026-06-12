# Project Status

**Last updated:** 2026-06-12
**Current stage:** 3b — SSM Engine (revised architecture)
**Branch:** claude/ssm-long-document-qa-jgbylw

---

## Architecture Revision (recorded at Stage 3b)

HuggingFace Mamba on CPU uses a Python-loop scan regardless of mode — token-by-token
recurrent ingest of large corpora is infeasible on CPU. Revised to Option A:

- `ingest` builds TF-IDF index only (no SSM checkpoint)
- `check` retrieves top-5 relevant law passages via TF-IDF, concatenates with
  statement (~1100 tokens total), runs ONE parallel Mamba forward pass, extracts
  cross-entropy for statement token positions only
- SSMEngine simplified to a single `forward(tokens) → log_probs` method

---

## Completed

- [x] Stage 0: `specs/01_user_spec.md` — APPROVED
- [x] Stage 1: `specs/02_system_spec.md` — APPROVED
- [x] Stage 2a–2e: all component specs — APPROVED
- [x] Stage 3a: Document Loader — APPROVED (all 5 AC passed on target hardware)

---

## In Progress

- [ ] Stage 3b: SSM Engine (revised) — awaiting eval results from target hardware

---

## Open Questions

None.

---

## Next Action

User runs `python tests/eval_engine.py`. Share full output including tok/s number.
