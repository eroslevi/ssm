from __future__ import annotations

from typing import Optional


def build_report(state: dict) -> dict:
    s1    = state.get("stage1_result")
    s2    = state.get("stage2_result")
    error = state.get("error")

    if s2 is not None:
        verdict = s2.get("verdict", "COMPLIANT")
    elif s1 is not None:
        raw = s1.get("verdict", "COMPLIANT")
        verdict = "PENDING" if raw == "VIOLATION" else raw
    else:
        verdict = "PENDING"

    return {
        "verdict":  verdict,
        "stage1":   _fmt(s1),
        "stage2":   _fmt(s2) if s2 is not None else None,
        "subgraph": s2.get("subgraph") if s2 else None,
        "error":    error or (s2.get("error") if s2 else None),
    }


def _fmt(result: Optional[dict]) -> Optional[dict]:
    if result is None:
        return None
    return {
        "verdict":          result.get("verdict", "COMPLIANT"),
        "violations":       result.get("violations", []),
        "checked_articles": result.get("checked_articles", []),
        "error":            result.get("error"),
    }
