from __future__ import annotations

from typing import Optional, Any
from langgraph.graph import StateGraph, END, START
from typing_extensions import TypedDict

from .config import Config, load_config
from .stage1 import Stage1Result, Stage1Violation, ArticleHit, run_stage1
from .stage2 import Stage2Result, Stage2Violation, Subgraph, run_stage2


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------

class CheckState(TypedDict):
    statement: str
    config: dict
    data_dir: str
    stage1_result: Optional[dict]
    stage2_result: Optional[dict]
    escalate: bool
    error: Optional[str]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def _stage1_node(state: CheckState) -> dict:
    cfg    = Config(**{k: v for k, v in state["config"].items()
                       if k in Config.__dataclass_fields__})
    result = run_stage1(state["statement"], cfg, state["data_dir"])
    return {"stage1_result": _s1_to_dict(result)}


def _stage2_node(state: CheckState) -> dict:
    cfg = Config(**{k: v for k, v in state["config"].items()
                    if k in Config.__dataclass_fields__})
    try:
        result = run_stage2(state["statement"], cfg, state["data_dir"])
        s2dict = _s2_to_dict(result)
        if result.error:
            return {"stage2_result": s2dict, "error": result.error}
        return {"stage2_result": s2dict}
    except Exception as exc:
        return {"stage2_result": None, "error": str(exc)}


def _route(state: CheckState) -> str:
    s1 = state.get("stage1_result") or {}
    if s1.get("verdict") == "COMPLIANT":
        return "stage2"
    if state.get("escalate"):
        return "stage2"
    return END


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def _build() -> Any:
    g = StateGraph(CheckState)
    g.add_node("stage1", _stage1_node)
    g.add_node("stage2", _stage2_node)
    g.add_edge(START, "stage1")
    g.add_conditional_edges("stage1", _route, {"stage2": "stage2", END: END})
    g.add_edge("stage2", END)
    return g.compile()


_graph: Any = None


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = _build()
    return _graph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_check(
    statement: str,
    escalate: bool = False,
    config_path: str = "config.yaml",
    data_dir: str = "data",
) -> CheckState:
    cfg = load_config(config_path)
    initial: CheckState = {
        "statement":     statement,
        "config":        cfg.__dict__,
        "data_dir":      data_dir,
        "stage1_result": None,
        "stage2_result": None,
        "escalate":      escalate,
        "error":         None,
    }
    return _get_graph().invoke(initial)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _s1_to_dict(r: Stage1Result) -> dict:
    return {
        "verdict":          r.verdict,
        "violations":       [v.__dict__ for v in r.violations],
        "checked_articles": [h.__dict__ for h in r.checked_articles],
    }


def _s2_to_dict(r: Stage2Result) -> dict:
    return {
        "verdict":          r.verdict,
        "violations":       [v.__dict__ for v in r.violations],
        "checked_articles": [h.__dict__ for h in r.checked_articles],
        "subgraph": {
            "nodes": r.subgraph.nodes,
            "edges": r.subgraph.edges,
        },
        "error": r.error,
    }
