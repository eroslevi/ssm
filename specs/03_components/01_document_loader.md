# Component Spec — Document Loader

**Stage:** 2a | **Status:** Awaiting approval

---

## Responsibility

Convert plain text files into token ID sequences consumed by the SSM Engine.
Two modes: chunked streaming (law corpus) and full load (statement).

---

## Interface

```python
class DocumentLoader:
    def __init__(self, tokenizer_name: str = "EleutherAI/gpt-neox-20b")

    def stream(self, path: str) -> Iterator[torch.Tensor]
    # Yields successive token chunks (internal buffer size, not user-configurable)
    # Each chunk shape: (n,) dtype=torch.long; final chunk may be shorter

    def load(self, path: str) -> torch.Tensor
    # Returns full token sequence, shape (n_tokens,) dtype=torch.long
    # For statement only — not for large files
```

---

## Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Tokenizer | `EleutherAI/gpt-neox-20b` | Matches Mamba pretraining vocabulary |
| File encoding | UTF-8 | Standard; error on non-UTF-8 input |
| Buffer size | Internal implementation detail | No effect on SSM output; chosen to keep RAM flat |
| RAM ceiling (stream) | Constant regardless of corpus size | OS-level buffering + fixed internal buffer |

---

## Data Structures

```python
# Token chunk (from stream)
torch.Tensor  shape=(chunk_tokens,)  dtype=torch.long

# Full statement tokens (from load)
torch.Tensor  shape=(n_tokens,)  dtype=torch.long
```

---

## Acceptance Criteria

| # | Test | Pass condition |
|---|------|---------------|
| 1 | Stream a 100 MB file | Peak RAM during streaming ≤ 200 MB above baseline |
| 2 | Round-trip | `decode(encode(text)) == text` for ASCII legal text |
| 3 | Chunk continuity | Concatenating all chunks gives same token sequence as `load()` on the same file |
| 4 | Short statement | `load()` on a 1000-character statement returns correct token count (roughly 200–300 tokens) |
| 5 | Empty file | Raises `ValueError` with clear message |

---

## Does this match your intent?
