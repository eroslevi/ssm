"""
Stage 3a evaluation — DocumentLoader acceptance criteria.

Run from the repo root:
    python tests/eval_loader.py

Expected output: all tests PASS.
"""

import sys
import tempfile
import tracemalloc
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssm_legal.loader import DocumentLoader

FIXTURES = Path(__file__).parent / "fixtures"
LAW_FILE = str(FIXTURES / "sample_laws.txt")
STMT_FILE = str(FIXTURES / "sample_statement.txt")


def _result(label: str, passed: bool, detail: str = "") -> None:
    tag = "PASS" if passed else "FAIL"
    print(f"  [{tag}] {label}" + (f": {detail}" if detail else ""))


def ac1_streaming_memory(loader: DocumentLoader) -> None:
    """Peak RAM during streaming stays constant regardless of file size."""
    tracemalloc.start()
    for _ in loader.stream(LAW_FILE):
        pass
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / 1_048_576
    _result("AC1 streaming memory", peak_mb < 200, f"peak {peak_mb:.1f} MB (limit 200 MB)")


def ac2_round_trip(loader: DocumentLoader) -> None:
    """decode(encode(text)) reproduces the original text (stripped)."""
    original = Path(STMT_FILE).read_text(encoding="utf-8").strip()
    tokens = loader.load(STMT_FILE)
    decoded = loader.tokenizer.decode(tokens.tolist()).strip()
    _result("AC2 round-trip", original == decoded, f"len {len(original)} vs {len(decoded)}")


def ac3_chunk_continuity(loader: DocumentLoader) -> None:
    """Concatenated stream chunks equal load() output."""
    chunks = list(loader.stream(LAW_FILE))
    streamed = torch.cat(chunks)
    loaded = loader.load(LAW_FILE)
    equal = torch.equal(streamed, loaded)
    _result(
        "AC3 chunk continuity",
        equal,
        f"streamed {streamed.shape[0]} tokens, loaded {loaded.shape[0]} tokens"
        + ("" if equal else " — mismatch (likely boundary artefact)"),
    )


def ac4_statement_token_count(loader: DocumentLoader) -> None:
    """A ~500-char statement tokenises to a plausible token count."""
    tokens = loader.load(STMT_FILE)
    n = tokens.shape[0]
    _result("AC4 statement token count", 50 <= n <= 500, f"{n} tokens")


def ac5_empty_file(loader: DocumentLoader) -> None:
    """Empty file raises ValueError with a clear message."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write("")
        tmp_path = tmp.name
    try:
        loader.load(tmp_path)
        _result("AC5 empty file", False, "no exception raised")
    except ValueError as exc:
        _result("AC5 empty file", True, str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def main() -> None:
    print("Loading tokenizer (first run downloads ~1 MB)...")
    loader = DocumentLoader()
    print(f"Tokenizer loaded. Vocab size: {loader.tokenizer.vocab_size}\n")
    print("Running acceptance criteria:")
    ac1_streaming_memory(loader)
    ac2_round_trip(loader)
    ac3_chunk_continuity(loader)
    ac4_statement_token_count(loader)
    ac5_empty_file(loader)
    print("\nDone. Share results for Stage 3a review gate.")


if __name__ == "__main__":
    main()
