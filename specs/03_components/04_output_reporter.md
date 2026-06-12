# Component Spec — Output Reporter

**Stage:** 2d | **Status:** Awaiting approval

---

## Responsibility

Render the list of `Violation` objects into a human-readable text report and a
JSON form consumed by the web frontend. Write to stdout and optionally to a file.

---

## Interface

```python
class OutputReporter:

    def render_text(self, violations: list[Violation]) -> str
    # Returns formatted plain-text report string

    def render_json(self, violations: list[Violation]) -> dict
    # Returns JSON-serialisable dict for the web frontend

    def write(self, violations: list[Violation],
              output_path: str | None = None) -> None
    # Prints render_text() to stdout
    # If output_path given, also saves render_text() to that file
```

---

## Text Report Format

```
=== COMPLIANCE REPORT ===
Verdict:    NON-COMPLIANT
Violations: 3

[1] Statement:   "the company retained 40% of client funds as undisclosed fees"
    Law:         "Article 12: all fees must be disclosed in writing prior to retention"
    Explanation: The statement's claim that '...' may conflict with '...'

[2] ...

=========================
```

For a compliant statement:
```
=== COMPLIANCE REPORT ===
Verdict:    COMPLIANT
Violations: 0
=========================
```

---

## JSON Format

```json
{
  "verdict": "NON-COMPLIANT",
  "violation_count": 3,
  "violations": [
    {
      "statement_excerpt": "...",
      "law_excerpt": "...",
      "explanation": "..."
    }
  ]
}
```

---

## Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Two render methods | `render_text` + `render_json` | CLI uses text; web frontend uses JSON |
| Stdout always printed | Yes | User sees result immediately without specifying a file |
| File output | Optional `.txt` | User may want a saved record |
| Verdict logic | COMPLIANT if `violations` is empty, else NON-COMPLIANT | Simple and unambiguous |

---

## Acceptance Criteria

| # | Test | Pass condition |
|---|------|---------------|
| 1 | Empty violations → COMPLIANT | `render_text([])` contains "COMPLIANT" and "Violations: 0" |
| 2 | Non-empty → NON-COMPLIANT | `render_text([v1, v2])` contains "NON-COMPLIANT" and both excerpts |
| 3 | File write | Given `output_path`, file is created with identical content to stdout |
| 4 | JSON round-trip | `render_json(violations)` is valid JSON and contains all violation fields |
| 5 | No truncation | Excerpts are not truncated regardless of length |

---

## Does this match your intent?
