# User Specification — SSM Legal Compliance Checker

**Stage:** 0 | **Status:** APPROVED

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

## Two-Mode Architecture

Because the law corpus is large and does not change between queries, processing is
split into two modes:

| Mode | Command | When to run |
|------|---------|-------------|
| `ingest` | `python -m ssm_legal ingest --laws laws.txt` | Once, when the law corpus is updated |
| `check` | `python -m ssm_legal check --statement statement.txt` | Every time a statement is evaluated |

`ingest` streams the law corpus through the SSM and saves the final hidden state
(a "law checkpoint") to disk. `check` restores that checkpoint and processes only
the statement against it.

---

## Inputs

| Mode | Input | Format | Size |
|------|-------|--------|------|
| `ingest` | Law corpus | Plain text `.txt` | Up to hundreds of MB |
| `check` | Company statement | Plain text `.txt` | Few hundred to ~1000 characters |

---

## Output (`check` mode)

A compliance report printed to the terminal and optionally saved to a `.txt` file:

1. **Verdict:** COMPLIANT or NON-COMPLIANT
2. **Violations list:** For each detected violation:
   - The offending passage from the statement (short excerpt)
   - The law or legal principle it conflicts with (short excerpt)
   - A one-sentence explanation of the conflict
3. **Summary count:** Number of violations found

---

## Performance Expectations

| Mode | Expected duration | Notes |
|------|-------------------|-------|
| `ingest` | Hours acceptable | Run once per law corpus version |
| `check` | Seconds | Statement is tiny; checkpoint is pre-computed |

---

## Constraints

- Runs on Windows 10/11, HP EliteBook class hardware (16 GB RAM, no dedicated GPU assumed)
- CPU execution required; CUDA acceleration optional if available
- No cloud calls, no external API dependencies
- Python 3.10+, installable via `pip` with a standard `requirements.txt`
- Single streaming pass — no retrieval loops at query time

---

## Web Frontend

A simple browser-based UI served locally (same machine). No cloud hosting. Two views:

| View | Purpose |
|------|---------|
| **Ingest** | Upload or specify path to law corpus `.txt`, trigger ingestion, show progress |
| **Check** | Paste or upload statement `.txt`, run compliance check, display report |

The frontend calls the same backend logic as the CLI. Running the tool starts a local
web server; the user opens `http://localhost:<port>` in their browser.

---

## Out of Scope

- Training or fine-tuning models
- Multi-language support (English only for prototype)
- PDF / DOCX parsing (plain text only)

---

## Does this match your intent?

Key decisions embedded here:
- Two-mode design: `ingest` (slow, once) and `check` (fast, per query)
- Simple local web frontend at `localhost` (no cloud)
- Plain text input only
- Hours acceptable for ingestion; seconds expected for check
- One-sentence violation explanations
