from __future__ import annotations

from typing import Callable, Iterator, Optional

import torch
from transformers import MambaForCausalLM


class SSMEngine:
    def __init__(
        self,
        model_name: str = "state-spaces/mamba-370m-hf",
        device: str = "cpu",
        dtype: torch.dtype = torch.float16,
    ):
        self.model = MambaForCausalLM.from_pretrained(
            model_name, torch_dtype=dtype
        ).to(device)
        self.model.eval()
        self.device = device
        self.dtype = dtype

    def ingest(
        self,
        token_stream: Iterator[torch.Tensor],
        checkpoint_path: str,
        on_progress: Optional[Callable[[int], None]] = None,
    ) -> None:
        """Stream law tokens through the SSM and save the final hidden state."""
        cache: Optional[MambaCache] = None
        tokens_processed = 0
        with torch.no_grad():
            for chunk in token_stream:
                input_ids = chunk.unsqueeze(0).to(self.device)
                out = self.model(input_ids, cache_params=cache, use_cache=True)
                cache = out.cache_params
                tokens_processed += chunk.shape[0]
                if on_progress:
                    on_progress(tokens_processed)
        _save_cache(cache, checkpoint_path)

    def check(
        self,
        tokens: torch.Tensor,
        checkpoint_path: str,
    ) -> torch.Tensor:
        """Restore law context, process statement, return per-token log-probs."""
        cache = _load_cache(checkpoint_path, self.model, self.device, self.dtype)
        input_ids = tokens.unsqueeze(0).to(self.device)
        with torch.no_grad():
            out = self.model(input_ids, cache_params=cache, use_cache=False)
        return torch.log_softmax(out.logits.squeeze(0), dim=-1)  # (n_tokens, vocab_size)


def _save_cache(cache: MambaCache, path: str) -> None:
    torch.save(
        {
            "seqlen_offset": cache.seqlen_offset,
            "conv_states": {k: v.cpu() for k, v in cache.conv_states.items()},
            "ssm_states": {k: v.cpu() for k, v in cache.ssm_states.items()},
        },
        path,
    )


def _load_cache(path: str, model: MambaForCausalLM, device: str, dtype: torch.dtype):
    saved = torch.load(path, map_location="cpu", weights_only=False)
    # Bootstrap a cache object via the model itself — avoids importing MambaCache directly,
    # which moves between transformers versions.
    dummy = torch.zeros(1, 1, dtype=torch.long, device=device)
    with torch.no_grad():
        cache = model(dummy, use_cache=True).cache_params
    cache.seqlen_offset = saved["seqlen_offset"]
    for k, v in saved["conv_states"].items():
        cache.conv_states[k] = v.to(device=device, dtype=dtype)
    for k, v in saved["ssm_states"].items():
        cache.ssm_states[k] = v.to(device=device, dtype=dtype)
    return cache
