# Component Spec — SSM Engine

**Stage:** 2b | **Status:** Awaiting approval

---

## Responsibility

Wrap a pretrained Mamba model running in recurrent inference mode. Two operations:
- `ingest`: consume the law token stream, accumulate hidden state, save to disk
- `check`: restore saved state, process statement tokens, return per-token log-probabilities

---

## Interface

```python
class SSMEngine:
    def __init__(self, model_name: str = "state-spaces/mamba-370m",
                 device: str = "cpu")

    def ingest(self, token_stream: Iterator[torch.Tensor],
               checkpoint_path: str) -> None
    # Processes full law token stream token-by-token in recurrent mode
    # Saves final hidden state to checkpoint_path

    def check(self, tokens: torch.Tensor,
              checkpoint_path: str) -> torch.Tensor
    # Loads hidden state from checkpoint_path
    # Processes statement tokens against restored law context
    # Returns log-probabilities, shape (n_statement_tokens, vocab_size)
```

---

## Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Model | `state-spaces/mamba-370m` | Fits in 16 GB RAM on CPU; strong enough for semantic retention |
| Inference mode | Recurrent (step-by-step) | Required for streaming; O(1) memory in hidden state |
| Volatility | Pretrained Δ values used as-is | No fine-tuning in prototype; Δ is input-dependent and learned |
| Checkpoint format | `torch.save` dict of conv_state + ssm_state tensors per layer | Native PyTorch, no extra dependencies |
| Device | CPU default, CUDA if available | On-prem laptop; CUDA accelerates ingest significantly if present |

---

## Checkpoint File Structure

```python
{
  "model_name": str,               # e.g. "state-spaces/mamba-370m"
  "conv_states": [Tensor, ...],    # one per layer, shape (batch, d_model, d_conv)
  "ssm_states":  [Tensor, ...],    # one per layer, shape (batch, d_state, d_inner)
}
# Saved with torch.save(), loaded with torch.load()
```

---

## Output Signal

`check()` returns per-token log-probabilities over the full vocabulary. The
Compliance Extractor uses these to compute per-token **cross-entropy** (negative
log-probability of the actual token) — a measure of how "surprising" each statement
token is given the accumulated law context. Spans with anomalously high cross-entropy
are candidates for compliance violations.

---

## Known Constraint

The pretrained Mamba model's Δ values were learned on general text, not legal
corpora. The prototype assumes the default volatility is sufficient for law context
retention. If it is not (measured during Stage 3b), Δ overrides or fine-tuning
will be considered at that point.

---

## Acceptance Criteria

| # | Test | Pass condition |
|---|------|---------------|
| 1 | Ingest produces checkpoint | `law_checkpoint.bin` exists after ingest, non-empty |
| 2 | Checkpoint round-trip | Loading saved state and re-running one token gives identical output to uninterrupted run |
| 3 | `check()` output shape | Returns tensor of shape `(n_tokens, vocab_size)` for any valid statement |
| 4 | Memory during ingest | Hidden state tensors in RAM; raw tokens not accumulated |
| 5 | CPU execution | Runs without CUDA installed; no GPU-only operations in critical path |

---

## Does this match your intent?
