# Component Spec — Stage2Agent

**Stage:** 2d | **Status:** APPROVED

---

## Responsibility

Deep remote analysis. Retrieves semantically similar PTK articles via FAISS,
expands the result set by following cross-reference edges in the knowledge graph,
then calls an Azure-hosted LLM to reason over the full legal subgraph.

---

## LangGraph Node Signature

```python
def stage2_node(state: CheckState) -> CheckState:
    """
    Input state fields:  statement (str), config (Config)
    Output state fields: stage2_result (Stage2Result)
    """
```

---

## Tools

### FAISSRetriever
```python
def retrieve(sentence: str, top_k: int) -> list[ArticleHit]:
    """
    Embeds sentence with multilingual-e5-base (same model used at ingest).
    Searches embeddings.faiss for top_k nearest vectors (cosine similarity).
    Fetches article rows from laws.db via faiss_idx.
    """
```

### GraphTraverser
```python
def expand(seed_ids: list[str], hops: int, max_articles: int) -> list[str]:
    """
    Executes hop-by-hop BFS over cross_refs table in laws.db.
    Returns union of seed_ids + all reachable article IDs within `hops` hops,
    capped at max_articles total. Seed articles ranked first.
    """
```

### AzureLLM
```python
def call(law_context: str, statement: str, config: Config) -> LLMResponse:
    """
    Calls Azure AI Foundry via OpenAI-compatible API.
    System prompt and user prompt template from config.yaml.
    Returns structured JSON parsed from LLM response.
    """
```

---

## Data Structures

```python
@dataclass
class Stage2Result:
    verdict: Literal["VIOLATION", "COMPLIANT"]
    violations: list[Stage2Violation]
    checked_articles: list[ArticleHit]
    subgraph: Subgraph              # for vis.js

@dataclass
class Stage2Violation:
    sentence: str
    article_ref: str                # "6:130"
    article_title: str
    article_excerpt: str
    paragraph_ref: str              # "6:130. § (2) bekezdés"
    explanation: str                # LLM-generated one sentence

@dataclass
class Subgraph:
    nodes: list[dict]               # {"id": "2013-5/6:130", "label": "6:130", "group": "seed"|"hop1"|"hop2"}
    edges: list[dict]               # {"from": ..., "to": ..., "label": "cross-ref"}
```

---

## Algorithm

```
for sentence in split_sentences(statement):
    seeds = FAISSRetriever.retrieve(sentence, top_k=config.top_k_stage2)
    expanded_ids = GraphTraverser.expand(
        [s.article_id for s in seeds],
        hops=config.graph_hops,
        max_articles=config.graph_max_articles
    )
    articles = fetch_articles(expanded_ids)          # from laws.db
    law_context = format_articles(articles)          # "6:130. § [Title]\n(1)..."
    response = AzureLLM.call(law_context, statement, config)

return Stage2Result from response + subgraph data
```

---

## LLM Prompt Contract

The LLM must return a JSON object:
```json
{
  "verdict": "VIOLATION" | "COMPLIANT",
  "violations": [
    {
      "sentence": "...",
      "article_ref": "6:130",
      "paragraph_ref": "6:130. § (2) bekezdés",
      "explanation": "..."
    }
  ],
  "checked_articles": ["6:130", "6:215"]
}
```

---

## Acceptance Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| AC1 | FAISS retrieval returns results | top-10 hits for any Hungarian sentence |
| AC2 | Graph traversal expands correctly | 2-hop expansion finds cross-referenced articles |
| AC3 | Max articles cap respected | never exceeds `graph_max_articles` articles sent to LLM |
| AC4 | Non-compliant statement → VIOLATION | `non_compliant.txt` flagged with PTK citation |
| AC5 | Compliant statement → COMPLIANT | `compliant.txt` returns COMPLIANT with checked articles |
| AC6 | Citation format correct | `article_ref` matches pattern `\d+:\d+` |
| AC7 | Latency | Stage 2 completes in < 30 seconds |
| AC8 | Azure error handled | API timeout returns Stage 1 result + warning, no crash |
