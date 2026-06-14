# Component Spec — Orchestrator

**Stage:** 2e | **Status:** APPROVED

---

## Responsibility

LangGraph state graph that manages the two-stage pipeline, routing between
Stage1Agent and Stage2Agent based on the Stage 1 verdict and user intent.

---

## State

```python
@dataclass
class CheckState(TypedDict):
    statement: str
    config: Config
    stage1_result: Stage1Result | None
    stage2_result: Stage2Result | None
    escalate: bool          # True when user manually requests Stage 2
```

---

## Graph Definition

```
[START]
   │
   ▼
stage1_node
   │
   ├─ VIOLATION + escalate=False ──────────────────► [END]
   │
   ├─ VIOLATION + escalate=True  ──────────────────► stage2_node ──► [END]
   │
   └─ COMPLIANT ────────────────────────────────────► stage2_node ──► [END]
```

Implemented as:

```python
graph = StateGraph(CheckState)
graph.add_node("stage1", stage1_node)
graph.add_node("stage2", stage2_node)
graph.add_edge(START, "stage1")
graph.add_conditional_edges("stage1", route_after_stage1)
graph.add_edge("stage2", END)
```

```python
def route_after_stage1(state: CheckState) -> str:
    if state.stage1_result.verdict == "COMPLIANT":
        return "stage2"
    if state.escalate:
        return "stage2"
    return END
```

---

## Config Loading

```python
@dataclass
class Config:
    nli_threshold: float = 0.85
    top_k_stage1: int = 5
    top_k_stage2: int = 10
    graph_hops: int = 2
    graph_max_articles: int = 50
    azure_endpoint: str = ""
    azure_api_key: str = ""
    azure_model: str = "gpt-4o"
    stage2_system_prompt: str = ""
    stage2_user_prompt: str = ""

def load_config(path: str = "config.yaml") -> Config: ...
```

---

## Public Interface

```python
def run_check(statement: str, escalate: bool = False) -> CheckState:
    """Entry point called by web server and CLI."""
    config = load_config()
    initial_state = CheckState(statement=statement, config=config,
                               stage1_result=None, stage2_result=None,
                               escalate=escalate)
    app = graph.compile()
    return app.invoke(initial_state)
```

---

## Acceptance Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| AC1 | COMPLIANT → auto Stage 2 | `stage2_result` populated when Stage 1 returns COMPLIANT |
| AC2 | VIOLATION → Stage 2 skipped | `stage2_result` is None when Stage 1 VIOLATION and escalate=False |
| AC3 | Manual escalation works | `stage2_result` populated when escalate=True regardless of Stage 1 |
| AC4 | Config loads from yaml | all fields read correctly from `config.yaml` |
| AC5 | Stage 2 error propagates cleanly | Azure failure returns state with `stage2_result=None` + error message |
