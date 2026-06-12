from __future__ import annotations

from typing import Iterator

import torch
from transformers import AutoTokenizer

_BUFFER_CHARS = 65_536  # 64 KB read buffer — internal detail, not exposed


class DocumentLoader:
    def __init__(self, tokenizer_name: str = "EleutherAI/gpt-neox-20b"):
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

    def stream(self, path: str) -> Iterator[torch.Tensor]:
        """Yield token-ID tensors from a large text file without loading it into RAM."""
        with open(path, "r", encoding="utf-8") as fh:
            remainder = ""
            while True:
                text = fh.read(_BUFFER_CHARS)
                if not text:
                    if remainder:
                        yield self._encode(remainder)
                    break
                combined = remainder + text
                # Always split at whitespace to avoid tokenisation artefacts at boundaries
                split = max(
                    combined.rfind(" "),
                    combined.rfind("\n"),
                    combined.rfind("\t"),
                )
                if split == -1:
                    remainder = ""
                    yield self._encode(combined)
                else:
                    yield self._encode(combined[: split + 1])
                    remainder = combined[split + 1 :]

    def load(self, path: str) -> torch.Tensor:
        """Load a small file fully and return its token IDs. Use for statements only."""
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        if not text.strip():
            raise ValueError(f"File is empty: {path}")
        return self._encode(text)

    def _encode(self, text: str) -> torch.Tensor:
        return self.tokenizer.encode(
            text,
            return_tensors="pt",
            add_special_tokens=False,
        ).squeeze(0)
