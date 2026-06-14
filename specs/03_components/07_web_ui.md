# Component Spec — Web UI

**Stage:** 2g | **Status:** APPROVED

---

## Responsibility

Local web server (FastAPI) and single-page HTML frontend. Provides the user
interface for ingestion and compliance checking.

---

## Endpoints

```
POST /ingest
  Body: {"file_path": "/path/to/ptk.txt"}
  Response: {"status": "ok", "articles": 1498, "duration_s": 47.2}

POST /check
  Body: {"statement": "...text..."}
  Response: Report (JSON, see Reporter spec)

POST /escalate
  Body: {"statement": "...text..."}
  Response: Report with stage2 populated
```

---

## Single-Page Layout

```
┌────────────────────────────────────────────────────┐
│  PTK Compliance Checker                            │
├────────────────────────────────────────────────────┤
│  [Statement text area, max 2000 chars]             │
│  [Check] button     char count: 0/2000             │
├────────────────────────────────────────────────────┤
│  STAGE 1 RESULT          │  STAGE 2 RESULT         │
│  ─────────────────────── │ ──────────────────────  │
│  Verdict: VIOLATION      │  (runs automatically    │
│                          │   or after button)      │
│  Sentence: "..."         │                         │
│  Article: 6:130. §       │  Verdict: VIOLATION     │
│  Excerpt: "..."          │  6:130. § (2) bekezdés  │
│                          │  Explanation: "..."     │
│  [Run deep analysis]     │                         │
├────────────────────────────────────────────────────┤
│  KNOWLEDGE SUBGRAPH  (vis.js, shown after Stage 2) │
│                                                    │
│   [6:130]──────►[6:215]                            │
│      └─────────►[5:1]                              │
│                                                    │
│  ● seed article  ○ hop-1  · hop-2                  │
└────────────────────────────────────────────────────┘
```

---

## Behaviour

- Statement textarea enforces 2,000 char limit (JS counter)
- "Check" calls `POST /check`, displays Stage 1 result
- If Stage 1 = COMPLIANT: `POST /escalate` fires automatically
- If Stage 1 = VIOLATION: "Run deep analysis" button visible; click calls `POST /escalate`
- Stage 2 result appends to right panel; subgraph renders below
- Loading spinner shown during both Stage 1 and Stage 2 calls
- Azure error: right panel shows "Deep analysis unavailable" warning

---

## Subgraph Visualization (vis.js)

- Nodes coloured by group: seed (blue), hop-1 (green), hop-2 (grey)
- Node label: `article_ref` (e.g. `6:130`)
- Tooltip on hover: article title
- Edges: directed arrows, labelled "cross-ref"
- Violation nodes highlighted in red
- Library loaded from CDN: `https://unpkg.com/vis-network`

---

## Technology

- FastAPI + uvicorn (Python)
- Single `index.html` file (vanilla JS, no build step)
- vis.js from CDN
- No Node.js, no npm

---

## Acceptance Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| AC1 | Server starts | `python -m ptk_check serve` → `http://localhost:8000` responds 200 |
| AC2 | Check endpoint works | `POST /check` with valid statement returns Report JSON |
| AC3 | Stage 2 auto-fires on COMPLIANT | right panel populated without user action |
| AC4 | "Run deep analysis" button appears | visible after Stage 1 VIOLATION |
| AC5 | Escalate button triggers Stage 2 | `POST /escalate` called on click, right panel updates |
| AC6 | Subgraph renders | vis.js canvas appears with nodes after Stage 2 |
| AC7 | Char limit enforced | submission blocked if textarea > 2000 chars |
| AC8 | Azure error handled | warning shown in right panel, no JS crash |
