from __future__ import annotations

import torch
from transformers import MambaForCausalLM


class SSMEngine:
    def __init__(
        self,
        model_name: str = "state-spaces/mamba-370m-hf",
        device: str = "cpu",
        dtype: torch.dtype = torch.float32,
    ):
        self.model = MambaForCausalLM.from_pretrained(
            model_name, torch_dtype=dtype
        ).to(device)
        self.model.eval()
        self.device = device
        self.dtype = dtype

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        """Single parallel forward pass. Returns log-probs (n_tokens, vocab_size).

        No cache_params → uses the parallel scan path, which batches all projections
        before the scan loop. Much faster on CPU than the recurrent (cache) path.
        """
        input_ids = tokens.unsqueeze(0).to(self.device)
        with torch.no_grad():
            out = self.model(input_ids)
        return torch.log_softmax(out.logits.squeeze(0), dim=-1)
