# Component Spec — Compliance Extractor

**Stage:** 2c | **Status:** Awaiting approval

---

## Responsibility

Two responsibilities split across the two tool modes:

- **`ingest` time:** build a TF-IDF index over the law corpus and save it to disk
- **`check` time:** detect non-compliant spans in the statement using cross-entropy,
  then attribute each span to the most relevant law passage using the pre-built index

---

## Data Structure

```python
@dataclass
class Violation:
    statement_excerpt: str   # flagged text span from the statement
    law_excerpt:       str   # most relevant law passage (from TF-IDF lookup)
    explanation:       str   # one-sentence template-based description
```

---

## Interface

```python
class ComplianceExtractor:

    # --- called once during ingest ---
    @staticmethod
    def build_index(laws_path: str, index_path: str) -> None
    # Splits law corpus into overlapping passages (~200 tokens, 50-token stride)
    # Fits TF-IDF vectorizer over passages
    # Saves vectorizer + passage texts to index_path (joblib)

    # --- called during check ---
    def __init__(self, index_path: str, threshold_std: float = 2.0)
    # Loads pre-built TF-IDF index from index_path
    # threshold_std: sensitivity dial — higher = fewer violations flagged

    def extract(self,
                tokens:    torch.Tensor,   # shape (n_tokens,)       — statement token IDs
                log_probs: torch.Tensor,   # shape (n_tokens, vocab_size) — from SSMEngine.check()
                tokenizer) -> list[Violation]
```

---

## Files on Disk

```
law_checkpoint.bin   ← SSM hidden state         (written by SSMEngine.ingest)
law_tfidf.pkl        ← TF-IDF index + passages  (written by ComplianceExtractor.build_index)
```

Both produced once during `ingest`, both loaded during `check`.

---

## Detection: Cross-Entropy Thresholding

```
CE[t] = -log_probs[t, tokens[t]]           # surprise of actual token given law context
threshold = mean(CE) + threshold_std * std(CE)
flagged tokens = { t : CE[t] > threshold }
flagged spans  = merge adjacent flagged tokens into contiguous text spans
```

---

## Attribution: TF-IDF Law Matching (pre-built index)

For each flagged statement span:
1. Query the pre-built TF-IDF index with the span text
2. Return top-1 law passage by cosine similarity → `law_excerpt`

Because the index is built during `ingest`, `check` queries are fast regardless
of law corpus size.

---

## Explanation Template

```
"The statement's claim that '{statement_excerpt}' may conflict with the
legal provision: '{law_excerpt}'."
```

---

## Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Index build time | `ingest` | Avoid rebuilding on every `check` call |
| Index format | joblib-serialised sklearn TF-IDF | Lightweight, pip-installable, fast query |
| Detection signal | Cross-entropy per token | Measures how surprising statement tokens are given law context |
| Flagging criterion | Mean + k·std | Adapts to statement; `k` is tunable |
| Attribution | TF-IDF cosine similarity | Lexical match — sufficient for prototype |
| Explanation | Template string | Avoids generative complexity in prototype |

---

## Acceptance Criteria

| # | Test | Pass condition |
|---|------|---------------|
| 1 | Index built during ingest | `law_tfidf.pkl` exists and is non-empty after ingest |
| 2 | No violations on compliant statement | Returns empty list for a statement that clearly follows the laws |
| 3 | Detects obvious violation | Returns ≥ 1 violation for a statement that directly contradicts a law |
| 4 | Excerpts are readable | `statement_excerpt` and `law_excerpt` are valid decoded text |
| 5 | Attribution is plausible | `law_excerpt` contains keywords overlapping with the flagged span |
| 6 | Threshold sensitivity | Lowering `threshold_std` increases violation count; raising it decreases it |

---

## Does this match your intent?
