# Component Spec — Compliance Extractor

**Stage:** 2c | **Status:** Awaiting approval

---

## Responsibility

Take the per-token log-probabilities produced by the SSM Engine over the statement
and identify which spans are non-compliant. For each flagged span, find the most
relevant law passage and produce a one-sentence explanation.

---

## Data Structure

```python
@dataclass
class Violation:
    statement_excerpt: str   # flagged text from the statement
    law_excerpt:       str   # most relevant law passage (attributed post-hoc)
    explanation:       str   # one-sentence template-based description
```

---

## Interface

```python
class ComplianceExtractor:
    def __init__(self, laws_path: str, threshold_std: float = 2.0)
    # laws_path: path to law corpus text (used for attribution only)
    # threshold_std: how many std above mean CE triggers a flag (sensitivity dial)

    def extract(self,
                tokens:    torch.Tensor,   # shape (n_tokens,)  — statement token IDs
                log_probs: torch.Tensor,   # shape (n_tokens, vocab_size) — from SSMEngine.check()
                tokenizer) -> list[Violation]
```

---

## Detection: Cross-Entropy Thresholding

```
CE[t] = -log_probs[t, tokens[t]]          # surprise of actual token given law context
threshold = mean(CE) + threshold_std * std(CE)
flagged tokens = { t : CE[t] > threshold }
flagged spans  = merge adjacent flagged tokens into contiguous text spans
```

Tokens with anomalously high cross-entropy are those the model found "surprising"
given the accumulated law context — candidates for non-compliance.

---

## Attribution: TF-IDF Law Matching

The SSM hidden state gives no direct pointer back to which law caused the flag.
Attribution is handled separately:

1. Split law corpus into overlapping passages (~200 tokens each, 50-token stride)
2. Build a TF-IDF index over those passages at init time
3. For each flagged statement span: retrieve the top-1 passage by TF-IDF similarity
4. That passage becomes `law_excerpt`

This keeps attribution lightweight and avoids re-running the SSM.

---

## Explanation Template

```
"The statement's claim that '{statement_excerpt}' may conflict with the
legal provision: '{law_excerpt}'."
```

Richer natural-language explanations can be added in a later iteration.

---

## Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Detection signal | Cross-entropy per token | Directly measures how surprising the statement is given law context |
| Flagging criterion | Mean + k·std | Adapts to statement length; `k` is tunable |
| Attribution method | TF-IDF on law passages | Simple, no extra model, sufficient for prototype |
| Explanation | Template string | Avoids generative complexity in prototype |
| Law index | Built at init, held in RAM | Passages are short; full index is small |

---

## Acceptance Criteria

| # | Test | Pass condition |
|---|------|---------------|
| 1 | No violations on compliant statement | Returns empty list for a statement that clearly follows the laws |
| 2 | Detects obvious violation | Returns ≥ 1 violation for a statement that directly contradicts a law |
| 3 | Excerpts are readable | `statement_excerpt` and `law_excerpt` are valid decoded text, not token IDs |
| 4 | Attribution is plausible | `law_excerpt` contains keywords overlapping with the flagged statement span |
| 5 | Threshold sensitivity | Lowering `threshold_std` increases violation count; raising it decreases it |

---

## Does this match your intent?
