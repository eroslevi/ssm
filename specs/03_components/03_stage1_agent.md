# Component Spec — Stage1Agent

**Stage:** 2c | **Status:** APPROVED

---

## Responsibility

Fast on-prem contradiction check. Splits the statement into sentences, retrieves
the most relevant PTK articles via TF-IDF, and scores each (article, sentence) pair
with a multilingual NLI model. Returns VIOLATION if any pair exceeds the threshold.

---

## LangGraph Node Signature

```python
def stage1_node(state: CheckState) -> CheckState:
    """
    Input state fields:  statement (str), config (Config)
    Output state fields: stage1_result (Stage1Result)
    """
```

---

## Tools

### TFIDFRetriever
```python
def retrieve(sentence: str, top_k: int) -> list[ArticleHit]:
    """
    Loads tfidf.pkl. Transforms sentence. Returns top_k article IDs + scores.
    Fetches full_text from laws.db for each hit.
    """
```

### NLIScorer
```python
def score(article_text: str, sentence: str) -> NLIScore:
    """
    Model: cross-encoder/mDeBERTa-v3-base-multilingual-nli-2mil7
    Input: (premise=article_text, hypothesis=sentence)
    Output: NLIScore(entailment, neutral, contradiction)
    contradiction field is the signal used for violation detection.
    """
```

---

## Data Structures

```python
@dataclass
class ArticleHit:
    article_id: str      # "2013-5/6:130"
    article_ref: str     # "6:130"
    title: str
    full_text: str
    tfidf_score: float

@dataclass
class NLIScore:
    entailment: float
    neutral: float
    contradiction: float

@dataclass
class Stage1Result:
    verdict: Literal["VIOLATION", "COMPLIANT"]
    violations: list[Stage1Violation]   # populated if verdict == VIOLATION
    checked_articles: list[ArticleHit]  # all articles consulted

@dataclass
class Stage1Violation:
    sentence: str
    article_ref: str         # "6:130"
    article_title: str
    article_excerpt: str     # first 300 chars of full_text
    contradiction_score: float
```

---

## Algorithm

```
for sentence in split_sentences(statement):
    hits = TFIDFRetriever.retrieve(sentence, top_k=config.top_k_stage1)
    for hit in hits:
        score = NLIScorer.score(hit.full_text, sentence)
        if score.contradiction >= config.nli_threshold:
            → add to violations, set verdict = VIOLATION
if any violations → return VIOLATION
else → return COMPLIANT
```

---

## Model

`cross-encoder/mDeBERTa-v3-base-multilingual-nli-2mil7`
- Size: ~560 MB
- Languages: Hungarian supported
- Auto-downloaded from HuggingFace on first run
- Runs on CPU; inference ~100–500 ms per pair

---

## Acceptance Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| AC1 | Model loads | no import or download error |
| AC2 | Compliant statement → COMPLIANT | 0 violations on `compliant.txt` fixture |
| AC3 | Non-compliant statement → VIOLATION | ≥ 1 violation on `non_compliant.txt` |
| AC4 | Excerpts readable | all `article_excerpt` are non-empty strings |
| AC5 | Threshold sensitivity | lowering threshold increases violation count |
| AC6 | Latency | Stage 1 completes in < 5 seconds on target hardware |
