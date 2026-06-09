# System Specification — SSM Legal Compliance Checker

**Stage:** 1 | **Status:** Awaiting approval

---

## System Overview

The system is a local Python application with two entry points — a CLI and a web
frontend — backed by the same core pipeline. The pipeline has two modes:

```
ingest mode:
  laws.txt → [Document Loader] → [SSM Engine] → law_checkpoint.bin

check mode:
  law_checkpoint.bin + statement.txt → [Document Loader] → [SSM Engine]
                                     → [Compliance Extractor] → [Output Reporter]
                                     → terminal / browser
```

---

## Components

### 1. Document Loader
Reads plain text files and converts them to token sequences.
- `ingest`: streams law corpus in chunks to avoid loading hundreds of MB into RAM
- `check`: loads the full statement (tiny, fits in memory)
- Outputs token ID tensors consumed by the SSM Engine

### 2. SSM Engine
Wraps a pretrained Mamba model running in recurrent (token-by-token) mode.

**Ingest mode:**
- Processes law tokens sequentially, maintaining hidden state
- Saves final hidden state to `law_checkpoint.bin` on disk

**Check mode:**
- Loads hidden state from `law_checkpoint.bin`
- Processes statement tokens against the restored state
- Outputs per-token hidden states and logits for the statement window

**Volatility:** Very low — Mamba's Δ (delta) is kept small so law context
persists through the full statement.

### 3. Compliance Extractor
Analyses the SSM output over the statement window to detect violations.
- Identifies spans in the statement where the model's output signals conflict
  with the accumulated law context (high perplexity or explicit flagging)
- For each flagged span: extracts the statement excerpt and the most
  contributing law context window
- Outputs a structured list of `Violation(statement_excerpt, law_excerpt, explanation)`

### 4. Output Reporter
Renders the violation list into a human-readable report.
- Formats COMPLIANT / NON-COMPLIANT verdict, violation list, summary count
- Writes to stdout and optionally to a `.txt` file
- Also provides a JSON-serialisable form consumed by the web frontend

### 5. Web Frontend
A lightweight local web server (FastAPI + single HTML page).
- **Ingest view:** file path input, trigger ingest, show live progress
- **Check view:** text area or file upload for statement, display report
- Shares the same Document Loader → SSM Engine → Extractor → Reporter pipeline

---

## Data Flow

```
laws.txt
  └─ Document Loader (chunked stream)
       └─ SSM Engine (recurrent pass, low Δ)
            └─ law_checkpoint.bin  ←── saved to disk

statement.txt + law_checkpoint.bin
  └─ Document Loader (full load)
       └─ SSM Engine (restore state, process statement)
            └─ per-token states + logits
                 └─ Compliance Extractor
                      └─ [Violation, ...]
                           └─ Output Reporter → stdout / .txt / JSON → web UI
```

---

## Technology Choices

| Concern | Choice | Reason |
|---------|--------|--------|
| SSM model | Mamba (state-spaces/mamba) | Best available pretrained SSM for text |
| Model size | Mamba-130M or Mamba-370M | Fits in 16 GB RAM on CPU |
| ML framework | PyTorch (CPU, optional CUDA) | Required by Mamba |
| Web server | FastAPI + uvicorn | Lightweight, pip-installable, Windows-compatible |
| Frontend | Single HTML file, vanilla JS | No build step, no Node dependency |
| Tokeniser | GPT-NeoX / EleutherAI (matches Mamba pretraining) | |

---

## File Layout

```
ssm/
├── CLAUDE.md
├── status.md
├── requirements.txt
├── specs/
│   ├── 01_user_spec.md
│   ├── 02_system_spec.md
│   └── 03_components/
├── src/
│   └── ssm_legal/
│       ├── __init__.py
│       ├── __main__.py        ← CLI entry point
│       ├── loader.py          ← Document Loader
│       ├── engine.py          ← SSM Engine
│       ├── extractor.py       ← Compliance Extractor
│       ├── reporter.py        ← Output Reporter
│       └── web/
│           ├── server.py      ← FastAPI app
│           └── index.html     ← Single-page frontend
└── tests/
    ├── fixtures/
    │   ├── sample_laws.txt
    │   └── sample_statement.txt
    └── test_*.py
```

---

## Does this match your intent?

Key decisions embedded here:
- Mamba-130M or 370M as the SSM backbone (pretrained, no training required)
- FastAPI + single HTML page for the web frontend (no Node.js, no build step)
- Checkpoint stored as a binary file on disk between ingest and check
- Compliance detection based on SSM output signal over the statement window

Please confirm or flag before component specs begin.
