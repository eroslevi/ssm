# User Specification — SSM Style Guide Compliance Checker

**Stage:** 0 | **Status:** APPROVED (updated for style guide use case, 2026-06-13)

---

## Purpose

A command-line tool that checks whether a document conforms to a provided style guide.
The tool runs entirely on-premises, requires no internet connection, and is designed to
handle style guides and documents of varying sizes without external API dependencies.

---

## Users

Writers, editors, content reviewers, or automated pipelines that need to verify whether
a document (e.g. a corporate report, client communication, or technical document) adheres
to a defined corporate or editorial style guide.

---

## Two-Mode Architecture

Because the style guide does not change between queries, processing is split into two modes:

| Mode | Command | When to run |
|------|---------|-------------|
| `ingest` | `python -m ssm_legal ingest --laws style_guide.txt` | Once, when the style guide is updated |
| `check` | `python -m ssm_legal check --statement document.txt` | Every time a document is evaluated |

`ingest` builds a retrieval index over the style guide. `check` retrieves the relevant
style guide sections and checks the document against them.

---

## Inputs

| Mode | Input | Format | Size |
|------|-------|--------|------|
| `ingest` | Style guide | Plain text `.txt` | Typically a few KB to hundreds of KB |
| `check` | Document to check | Plain text `.txt` | Few hundred to ~1000 characters |

---

## Output (`check` mode)

A style compliance report printed to the terminal and optionally saved to a `.txt` file:

1. **Verdict:** COMPLIANT or NON-COMPLIANT
2. **Violations list:** For each detected violation:
   - The offending passage from the document (short excerpt)
   - The style rule it conflicts with (short excerpt from style guide)
   - A one-sentence explanation of the conflict
3. **Summary count:** Number of violations found

---

## Performance Expectations

| Mode | Expected duration | Notes |
|------|-------------------|-------|
| `ingest` | Seconds | Style guides are small; index builds fast |
| `check` | Seconds | Short documents; retrieval + single model pass |

---

## Constraints

- Runs on Windows 10/11, HP EliteBook class hardware (16 GB RAM, no dedicated GPU assumed)
- CPU execution required; CUDA acceleration optional if available
- No cloud calls, no external API dependencies
- Python 3.10+, installable via `pip` with a standard `requirements.txt`
- English language style guides for prototype

---

## Web Frontend

A simple browser-based UI served locally (same machine). No cloud hosting. Two views:

| View | Purpose |
|------|---------|
| **Ingest** | Upload or specify path to style guide `.txt`, trigger indexing, show progress |
| **Check** | Paste or upload document `.txt`, run style check, display report |

The frontend calls the same backend logic as the CLI. Running the tool starts a local
web server; the user opens `http://localhost:<port>` in their browser.

---

## Out of Scope

- Training or fine-tuning models
- Multi-language support (English only for prototype)
- PDF / DOCX parsing (plain text only)
