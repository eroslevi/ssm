"""
Stage 3b evaluation — SSMEngine acceptance criteria.

Run from the repo root:
    python tests/eval_engine.py

First run downloads ~750 MB model weights from HuggingFace (one-time).
Results include throughput measurement — share the full output for review.
"""

import sys
import tempfile
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


def ac1_checkpoint_created(engine: SSMEngine, loader: DocumentLoader) -> str:
    """Checkpoint file is created after ingest."""
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        ckpt = tmp.name
    t0 = time.time()
    token_count = [0]

    def progress(n: int) -> None:
        token_count[0] = n

    engine.ingest(loader.stream(LAW_FILE), ckpt, on_progress=progress)
    elapsed = time.time() - t0
    size_kb = Path(ckpt).stat().st_size / 1024
    throughput = token_count[0] / elapsed if elapsed > 0 else 0
    exists = Path(ckpt).exists() and size_kb > 0
    _result(
        "AC1 checkpoint created",
        exists,
        f"{size_kb:.0f} KB, {token_count[0]} tokens in {elapsed:.1f}s "
        f"({throughput:.0f} tok/s)",
    )
    return ckpt


def ac2_checkpoint_round_trip(engine: SSMEngine, loader: DocumentLoader, ckpt: str) -> None:
    """Loading the checkpoint twice gives identical log-probs (determinism)."""
    tokens = loader.load(STMT_FILE)
    lp1 = engine.check(tokens, ckpt)
    lp2 = engine.check(tokens, ckpt)
    equal = torch.allclose(lp1, lp2, atol=1e-4)
    _result("AC2 checkpoint round-trip", equal,
            f"max diff {(lp1 - lp2).abs().max().item():.2e}")


def ac3_output_shape(engine: SSMEngine, loader: DocumentLoader, ckpt: str) -> None:
    """check() returns shape (n_tokens, vocab_size)."""
    tokens = loader.load(STMT_FILE)
    log_probs = engine.check(tokens, ckpt)
    n_tok = tokens.shape[0]
    vocab = engine.model.config.vocab_size
    correct = log_probs.shape == (n_tok, vocab)
    _result("AC3 output shape", correct, f"{tuple(log_probs.shape)} expected ({n_tok}, {vocab})")


def ac4_memory_during_ingest(engine: SSMEngine, loader: DocumentLoader) -> None:
    """Token buffer not accumulated in RAM during ingest."""
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        ckpt = tmp.name
    tracemalloc.start()
    engine.ingest(loader.stream(LAW_FILE), ckpt)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / 1_048_576
    _result("AC4 memory during ingest", peak_mb < 500,
            f"peak {peak_mb:.1f} MB (limit 500 MB)")
    Path(ckpt).unlink(missing_ok=True)


def ac5_cpu_execution(engine: SSMEngine) -> None:
    """Model and tensors reside on CPU."""
    params_on_cpu = all(p.device.type == "cpu" for p in engine.model.parameters())
    _result("AC5 CPU execution", params_on_cpu,
            f"device: {next(engine.model.parameters()).device}")


def main() -> None:
    print("Loading model (first run downloads ~750 MB)...")
    loader = DocumentLoader()
    engine = SSMEngine()
    print(f"Model loaded. Layers: {engine.model.config.num_hidden_layers}, "
          f"d_model: {engine.model.config.hidden_size}\n")

    print("Running acceptance criteria:")
    ckpt = ac1_checkpoint_created(engine, loader)
    ac2_checkpoint_round_trip(engine, loader, ckpt)
    ac3_output_shape(engine, loader, ckpt)
    ac4_memory_during_ingest(engine, loader)
    ac5_cpu_execution(engine)

    Path(ckpt).unlink(missing_ok=True)
    print("\nDone. Share results for Stage 3b review gate.")


if __name__ == "__main__":
    main()
