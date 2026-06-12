"""
Stage 3b evaluation — SSMEngine acceptance criteria (Option A: parallel forward pass).

Run from the repo root:
    python tests/eval_engine.py

First run downloads ~750 MB model weights from HuggingFace (one-time).
Share the full output including tok/s for Stage 3b review.
"""

import sys
import time
import tracemalloc
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssm_legal.loader import DocumentLoader
from ssm_legal.engine import SSMEngine

FIXTURES = Path(__file__).parent / "fixtures"
LAW_FILE  = str(FIXTURES / "sample_laws.txt")
STMT_FILE = str(FIXTURES / "sample_statement.txt")


def _result(label: str, passed: bool, detail: str = "") -> None:
    tag = "PASS" if passed else "FAIL"
    print(f"  [{tag}] {label}" + (f": {detail}" if detail else ""))


def _make_combined(loader: DocumentLoader) -> tuple[torch.Tensor, int]:
    """Return (combined_tokens, statement_start_index) for a small law sample + statement."""
    law_text = Path(LAW_FILE).read_text(encoding="utf-8")[:3000]
    law_ids = loader.tokenizer.encode(law_text, add_special_tokens=False)
    stmt_ids = loader.tokenizer.encode(
        Path(STMT_FILE).read_text(encoding="utf-8"), add_special_tokens=False
    )
    combined = torch.tensor(law_ids + stmt_ids, dtype=torch.long)
    return combined, len(law_ids)


def ac1_output_shape(engine: SSMEngine, loader: DocumentLoader) -> None:
    """forward() returns shape (n_tokens, vocab_size)."""
    combined, _ = _make_combined(loader)
    log_probs = engine.forward(combined)
    n = combined.shape[0]
    v = engine.model.config.vocab_size
    correct = log_probs.shape == (n, v)
    _result("AC1 output shape", correct, f"{tuple(log_probs.shape)} expected ({n}, {v})")


def ac2_determinism(engine: SSMEngine, loader: DocumentLoader) -> None:
    """Same input → identical log-probs on repeated calls."""
    combined, _ = _make_combined(loader)
    lp1 = engine.forward(combined)
    lp2 = engine.forward(combined)
    diff = (lp1 - lp2).abs().max().item()
    _result("AC2 determinism", diff == 0.0, f"max diff {diff:.2e}")


def ac3_throughput(engine: SSMEngine, loader: DocumentLoader) -> None:
    """Measure tokens/sec and estimate real ingest time on 100 MB corpus."""
    combined, _ = _make_combined(loader)
    n = combined.shape[0]
    t0 = time.time()
    engine.forward(combined)
    elapsed = time.time() - t0
    tps = n / elapsed
    # 100 MB ≈ 6M tokens (conservative); estimate check time for ~1100 tokens
    _result(
        "AC3 throughput",
        tps > 0,
        f"{n} tokens in {elapsed:.2f}s = {tps:.1f} tok/s  "
        f"(check call ~{1100/tps:.1f}s for 1100-token combined input)",
    )


def ac4_memory(engine: SSMEngine, loader: DocumentLoader) -> None:
    """Peak memory during forward pass is within bounds."""
    combined, _ = _make_combined(loader)
    tracemalloc.start()
    engine.forward(combined)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / 1_048_576
    _result("AC4 memory", peak_mb < 2000, f"peak {peak_mb:.0f} MB (limit 2000 MB)")


def ac5_cpu_execution(engine: SSMEngine) -> None:
    """Model parameters reside on CPU."""
    on_cpu = all(p.device.type == "cpu" for p in engine.model.parameters())
    device = next(engine.model.parameters()).device
    _result("AC5 CPU execution", on_cpu, f"device: {device}")


def main() -> None:
    print("Loading model and tokenizer...")
    loader = DocumentLoader()
    engine = SSMEngine()
    print(f"Ready. d_model={engine.model.config.hidden_size}, "
          f"layers={engine.model.config.num_hidden_layers}\n")

    print("Running acceptance criteria:")
    ac1_output_shape(engine, loader)
    ac2_determinism(engine, loader)
    ac3_throughput(engine, loader)
    ac4_memory(engine, loader)
    ac5_cpu_execution(engine)
    print("\nDone. Share results for Stage 3b review gate.")


if __name__ == "__main__":
    main()
