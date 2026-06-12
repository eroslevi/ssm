# Component Spec — Web Frontend

**Stage:** 2e | **Status:** Awaiting approval

---

## Responsibility

A locally-served single-page web app that exposes the `ingest` and `check`
pipeline through a browser UI. No cloud, no Node.js, no build step.

---

## Interface

```python
# src/ssm_legal/web/server.py

def create_app(checkpoint_dir: str) -> FastAPI
# Returns configured FastAPI app
# checkpoint_dir: directory where law_checkpoint.bin and law_tfidf.pkl are stored

# Entry point:
# python -m ssm_legal serve --checkpoint-dir ./checkpoints --port 8000
```

---

## API Endpoints

| Method | Path | Body | Response |
|--------|------|------|----------|
| `GET` | `/` | — | `index.html` |
| `POST` | `/ingest` | `{"laws_path": "C:/path/to/laws.txt"}` | `{"job_id": "..."}` |
| `GET` | `/ingest/status` | — | `{"status": "idle"\|"running"\|"done"\|"error", "message": "..."}` |
| `POST` | `/check` | `{"statement": "...text..."}` | JSON report (OutputReporter.render_json) |

`/ingest` starts the ingest pipeline in a background thread and returns immediately.
`/check` runs synchronously — fast since the statement is tiny.

---

## Frontend Layout (index.html)

Single HTML file, vanilla JS, no external dependencies beyond a minimal CSS reset.

```
┌─────────────────────────────────────┐
│  SSM Legal Compliance Checker       │
│  [Ingest Laws] [Check Statement]    │  ← tab strip
├─────────────────────────────────────┤
│  INGEST TAB                         │
│  Law corpus path: [_______________] │
│  [Run Ingest]                       │
│  Status: running... / done / error  │
├─────────────────────────────────────┤
│  CHECK TAB                          │
│  Statement: [text area            ] │
│  [Check Compliance]                 │
│  ┌─────────────────────────────┐    │
│  │ Verdict: NON-COMPLIANT      │    │
│  │ [1] Statement: "..."        │    │
│  │     Law: "..."              │    │
│  │     "...explanation..."     │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

---

## Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Law input | File path (not file upload) | Law corpus can be hundreds of MB — browser upload impractical |
| Statement input | Text area | Statement is tiny; paste is simpler than file upload |
| Progress | Browser polls `/ingest/status` every 3 s | Simple; avoids SSE/WebSocket complexity |
| Background ingest | `threading.Thread` | Keeps FastAPI responsive during long ingest |
| Port | 8000 (configurable) | Standard local dev port |
| Single HTML file | Inline CSS + JS | No build step, no npm |

---

## Acceptance Criteria

| # | Test | Pass condition |
|---|------|---------------|
| 1 | Server starts | `python -m ssm_legal serve` opens without error; `http://localhost:8000` returns 200 |
| 2 | Ingest via UI | Providing a valid law corpus path and clicking Run Ingest produces `law_checkpoint.bin` and `law_tfidf.pkl` |
| 3 | Progress display | Status updates from "running" to "done" in the browser without page reload |
| 4 | Check via UI | Pasting a statement and clicking Check returns a rendered report in the browser |
| 5 | Windows compatibility | Server starts and serves correctly on Windows without POSIX-specific dependencies |

---

## Does this match your intent?
