# Project Status

**Last updated:** 2026-06-13
**Current stage:** 3c — Compliance Extractor evaluation (style guide use case)
**Branch:** claude/ssm-long-document-qa-jgbylw

---

## Use Case Pivot (recorded 2026-06-13)

Original target: Hungarian Polgári Törvénykönyv legal compliance.
Revised target: **Corporate style guide compliance checking.**

Reason: CE from a general pretrained LM measures linguistic surprise, not legal
contradiction. Style violations ARE linguistic anomalies (passive voice, prohibited
words, weak qualifiers), so CE is the right signal for style checking. Legal compliance
violations can be grammatically perfect sentences — CE misses them entirely.

The architecture is identical. Only fixtures and framing changed.

---

## Architecture Revision (recorded at Stage 3b)

HuggingFace Mamba on CPU uses a Python-loop scan regardless of mode — token-by-token
recurrent ingest is infeasible. Revised to Option A:

- `ingest` builds TF-IDF index only (no SSM checkpoint)
- `check` retrieves top-5 style guide passages via TF-IDF, runs ONE parallel Mamba
  forward pass over [passages | document], extracts cross-entropy for document positions
- SSMEngine simplified to `forward(tokens) → log_probs`

---

## Completed

- [x] Stage 0: `specs/01_user_spec.md` — APPROVED (updated for style guide use case)
- [x] Stage 1: `specs/02_system_spec.md` — APPROVED
- [x] Stage 2a–2e: all component specs — APPROVED
- [x] Stage 3a: Document Loader — APPROVED (all 5 AC passed)
- [x] Stage 3b: SSM Engine — APPROVED (103.6 tok/s, ~10s per check call on target hardware)

---

## In Progress

- [ ] Stage 3c: Compliance Extractor — fixtures updated for style guide, awaiting eval results

---

## Open Questions

None.

---

## Next Action

User runs `python tests/eval_extractor.py`. Share full output for Stage 3c review.
