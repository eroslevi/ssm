# Component Spec — Reporter

**Stage:** 2f | **Status:** APPROVED

---

## Responsibility

Converts `CheckState` from the orchestrator into a JSON structure consumed
by the web UI. No rendering logic — the web UI handles display.

---

## Interface

```python
def build_report(state: CheckState) -> Report:
    """
    Combines Stage 1 and Stage 2 results into a single Report.
    Called by the web server after run_check() returns.
    """
```

---

## Output Structure

```python
@dataclass
class Report:
    verdict: Literal["VIOLATION", "COMPLIANT", "PENDING"]
    # PENDING = Stage 1 VIOLATION, Stage 2 not yet run

    stage1: StageReport
    stage2: StageReport | None      # None if not run or failed

    subgraph: Subgraph | None       # from Stage2Result, for vis.js

@dataclass
class StageReport:
    verdict: Literal["VIOLATION", "COMPLIANT"]
    violations: list[ViolationEntry]
    checked_articles: list[ArticleSummary]
    error: str | None               # set if stage failed

@dataclass
class ViolationEntry:
    sentence: str                   # offending sentence from statement
    article_ref: str                # "6:130"
    article_title: str              # "Kártérítési kötelezettség"
    article_excerpt: str            # first 300 chars of article text
    paragraph_ref: str              # "6:130. § (2) bekezdés" (Stage 2 only)
    explanation: str                # one-sentence conflict description
    score: float | None             # NLI contradiction score (Stage 1 only)

@dataclass
class ArticleSummary:
    article_ref: str
    article_title: str
```

---

## Rules

- If `stage2_result` is present, it determines the top-level `verdict`
- If only `stage1_result` is present, `verdict = stage1_result.verdict`
  with `verdict = "PENDING"` when Stage 1 is VIOLATION and Stage 2 not run
- `ViolationEntry.paragraph_ref` is empty string for Stage 1 violations
  (NLI does not identify specific paragraphs)
- All text fields are plain strings — no HTML escaping here

---

## Acceptance Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| AC1 | Report is JSON-serialisable | `json.dumps(report)` succeeds |
| AC2 | Stage 1 only verdict correct | VIOLATION when Stage 1 VIOLATION + no Stage 2 |
| AC3 | Stage 2 overrides Stage 1 | Stage 2 verdict used as top-level when present |
| AC4 | Checked articles present on COMPLIANT | `checked_articles` non-empty on COMPLIANT |
| AC5 | Subgraph present after Stage 2 | `subgraph.nodes` non-empty after Stage 2 run |
