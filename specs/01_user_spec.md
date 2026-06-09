# User Specification — SSM Legal Compliance Checker

**Stage:** 0 | **Status:** Awaiting approval

---

## Purpose

A command-line tool that checks whether a company statement is compliant with a
provided corpus of laws. The tool runs entirely on-premises, requires no internet
connection, and is designed to handle law corpora that are too large for standard
context-window-based approaches.

---

## Users

Compliance officers, legal reviewers, or automated pipelines that need to verify
whether a client-facing company statement (e.g. a bookkeeping report) adheres to
applicable law.

---

## Inputs

| Input | Format | Size expectation |
|-------|--------|-----------------|
| Law corpus | Plain text file (`.txt`) | Large — up to hundreds of MB |
| Company statement | Plain text file (`.txt`) | Small — tens of KB to low MB |

Both inputs are provided as separate files. The tool concatenates them internally
in the order: laws first, statement second.

---

## Output

A compliance report printed to the terminal and optionally saved to a `.txt` file,
containing:

1. **Verdict:** COMPLIANT or NON-COMPLIANT
2. **Violations list:** For each detected violation:
   - The offending passage from the statement (short excerpt)
   - The law or legal principle it conflicts with (short excerpt)
   - A one-sentence explanation of the conflict
3. **Summary count:** Number of violations found

---

## Constraints

- Runs on Windows 10/11, HP EliteBook class hardware (16 GB RAM, no dedicated GPU assumed)
- CPU execution required; CUDA acceleration optional if available
- No cloud calls, no external API dependencies
- Python 3.10+, installable via `pip` with a standard `requirements.txt`
- Single-pass processing — no iterative retrieval loops
- Startup + processing time target: under 5 minutes for a 100 MB law corpus + 50 KB statement on CPU

---

## Out of Scope

- Training or fine-tuning models
- Multi-language support (English only for prototype)
- GUI or web interface
- Real-time / streaming input

---

## Does this match your intent?

Key decisions embedded here:
- Separate input files (not pre-concatenated by the user)
- Plain text only (no PDF/DOCX parsing)
- Terminal output, optional file save
- 5-minute processing budget on CPU

Please confirm or flag any of the above before Stage 1 begins.
