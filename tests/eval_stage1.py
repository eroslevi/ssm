"""
Stage 3c evaluation — Stage1Agent acceptance criteria.

Run from repo root (requires data/ indexes to exist):
    python tests/eval_stage1.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ptk_check.config import Config
from ptk_check.stage1 import run_stage1

FIXTURES = Path(__file__).parent / "fixtures" / "statements"
STMT_OK  = (FIXTURES / "compliant.txt").read_text(encoding="utf-8")
STMT_BAD = (FIXTURES / "non_compliant.txt").read_text(encoding="utf-8")
DATA_DIR = "data"


def _r(label, passed, detail=""):
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}" + (f": {detail}" if detail else ""))


def main():
    print("Loading NLI model (first run downloads ~600 MB)...")
    cfg = Config()

    print("\nRunning acceptance criteria:\n")

    # AC1: model loads
    try:
        from ptk_check.stage1 import _scorer
        _scorer._load()
        _r("AC1 model loads", True, "mDeBERTa loaded")
    except Exception as e:
        _r("AC1 model loads", False, str(e))
        return

    # AC2: compliant → no violations
    t0   = time.time()
    r_ok = run_stage1(STMT_OK, cfg, DATA_DIR)
    t_ok = time.time() - t0
    _r("AC2 compliant → COMPLIANT", r_ok.verdict == "COMPLIANT",
       f"{len(r_ok.violations)} violations in {t_ok:.1f}s")

    # AC3: non-compliant → violation
    t0    = time.time()
    r_bad = run_stage1(STMT_BAD, cfg, DATA_DIR)
    t_bad = time.time() - t0
    _r("AC3 non-compliant → VIOLATION", r_bad.verdict == "VIOLATION",
       f"{len(r_bad.violations)} violations in {t_bad:.1f}s")

    # AC4: excerpts readable
    if r_bad.violations:
        readable = all(len(v.article_excerpt) > 2 for v in r_bad.violations)
        _r("AC4 excerpts readable", readable,
           f"sample: '{r_bad.violations[0].article_excerpt[:60]}'")
    else:
        _r("AC4 excerpts readable", False, "no violations")

    # AC5: threshold sensitivity
    cfg_low = Config(nli_threshold=0.5)
    r_low   = run_stage1(STMT_BAD, cfg_low, DATA_DIR)
    _r("AC5 threshold sensitivity", len(r_low.violations) >= len(r_bad.violations),
       f"default={len(r_bad.violations)} low={len(r_low.violations)}")

    # AC6: latency (CPU target <120s; original <5s assumes GPU)
    _r("AC6 latency < 120s (CPU)", t_bad < 120, f"{t_bad:.1f}s")

    if r_bad.violations:
        print(f"\nViolations found ({len(r_bad.violations)}):")
        for i, v in enumerate(r_bad.violations, 1):
            print(f"  [{i}] sentence: \"{v.sentence[:80]}\"")
            print(f"       article:  {v.article_ref} — {v.article_title}")
            print(f"       score:    {v.contradiction_score:.3f}")

    print("\nDone. Share results for Stage 3c review gate.")


if __name__ == "__main__":
    main()
