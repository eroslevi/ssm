"""
Stage 3c evaluation — ComplianceExtractor acceptance criteria.

Run from the repo root:
    python tests/eval_extractor.py

Requires model weights already downloaded (run eval_engine.py first).
Share the full output for Stage 3c review gate.
"""

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ssm_legal.loader import DocumentLoader
from ssm_legal.engine import SSMEngine
from ssm_legal.extractor import ComplianceExtractor

FIXTURES     = Path(__file__).parent / "fixtures"
LAW_FILE     = str(FIXTURES / "sample_laws.txt")
STMT_NON     = (FIXTURES / "sample_statement.txt").read_text(encoding="utf-8")
STMT_OK      = (FIXTURES / "compliant_statement.txt").read_text(encoding="utf-8")


def _result(label: str, passed: bool, detail: str = "") -> None:
    tag = "PASS" if passed else "FAIL"
    print(f"  [{tag}] {label}" + (f": {detail}" if detail else ""))


def main() -> None:
    print("Loading model and tokenizer...")
    loader = DocumentLoader()
    engine = SSMEngine()

    # Build index into a temp file
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        index_path = tmp.name

    print("\nBuilding TF-IDF index...")
    t0 = time.time()
    ComplianceExtractor.build_index(LAW_FILE, index_path)
    print(f"  built in {time.time() - t0:.2f}s")

    extractor = ComplianceExtractor(index_path, engine, loader.tokenizer)

    print("\nRunning acceptance criteria:")

    # AC1: index file created and non-empty
    size_kb = Path(index_path).stat().st_size / 1024
    _result("AC1 index created", size_kb > 0, f"{size_kb:.1f} KB")

    # AC2: compliant statement → no violations
    t0 = time.time()
    v_ok = extractor.extract(STMT_OK)
    elapsed_ok = time.time() - t0
    _result("AC2 compliant → no violations", len(v_ok) == 0,
            f"{len(v_ok)} violations in {elapsed_ok:.1f}s")

    # AC3: non-compliant statement → at least 1 violation
    t0 = time.time()
    v_non = extractor.extract(STMT_NON)
    elapsed_non = time.time() - t0
    _result("AC3 non-compliant → violations detected", len(v_non) >= 1,
            f"{len(v_non)} violations in {elapsed_non:.1f}s")

    # AC4: excerpts are readable text (not token IDs or empty)
    if v_non:
        readable = all(
            isinstance(v.statement_excerpt, str) and len(v.statement_excerpt) > 2
            and isinstance(v.law_excerpt, str) and len(v.law_excerpt) > 2
            for v in v_non
        )
        _result("AC4 excerpts readable", readable,
                f"sample: '{v_non[0].statement_excerpt[:60]}'")
    else:
        _result("AC4 excerpts readable", False, "no violations to inspect")

    # AC5: attribution plausible — law_excerpt shares keywords with statement_excerpt
    if v_non:
        def keyword_overlap(a: str, b: str) -> int:
            words_a = {w.lower() for w in a.split() if len(w) > 4}
            words_b = {w.lower() for w in b.split() if len(w) > 4}
            return len(words_a & words_b)
        overlaps = [keyword_overlap(v.statement_excerpt, v.law_excerpt) for v in v_non]
        plausible = any(o > 0 for o in overlaps)
        _result("AC5 attribution plausible", plausible,
                f"keyword overlaps per violation: {overlaps}")
    else:
        _result("AC5 attribution plausible", False, "no violations to inspect")

    # AC6: threshold sensitivity — lower threshold → more violations
    extractor_sensitive = ComplianceExtractor(index_path, engine, loader.tokenizer,
                                              threshold_std=0.5)
    v_sensitive = extractor_sensitive.extract(STMT_NON)
    _result("AC6 threshold sensitivity", len(v_sensitive) >= len(v_non),
            f"default({extractor.threshold_std}σ)={len(v_non)}  "
            f"sensitive(0.5σ)={len(v_sensitive)}")

    # Print violation details
    if v_non:
        print(f"\nViolations found in non-compliant statement ({len(v_non)}):")
        for i, v in enumerate(v_non, 1):
            print(f"  [{i}] Statement: \"{v.statement_excerpt[:80]}\"")
            print(f"       Law:       \"{v.law_excerpt[:80]}\"")
            print(f"       {v.explanation[:120]}")

    Path(index_path).unlink(missing_ok=True)
    print("\nDone. Share results for Stage 3c review gate.")


if __name__ == "__main__":
    main()
