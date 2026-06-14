"""
Stage 3a evaluation — LawParser acceptance criteria.

Run from repo root:
    python tests/eval_parser.py path/to/ptk.txt
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ptk_check.parser import parse_ptk


def _r(label, passed, detail=""):
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}" + (f": {detail}" if detail else ""))


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/eval_parser.py path/to/ptk.txt", file=sys.stderr)
        sys.exit(1)
    PTK_FILE = sys.argv[1]
    print(f"Parsing {PTK_FILE} ...")
    articles = parse_ptk(PTK_FILE)
    print(f"  → {len(articles)} articles parsed\n")
    print("Running acceptance criteria:")

    _r("AC1 article count ≥ 1400", len(articles) >= 1400, f"{len(articles)} articles")

    books = {a.book_num for a in articles}
    _r("AC2 all 8 books present", books == set(range(1, 9)), f"books found: {sorted(books)}")

    refs = [a.article_ref for a in articles]
    _r("AC3 article refs unique", len(refs) == len(set(refs)),
       f"{len(refs) - len(set(refs))} duplicates")

    total_xrefs = sum(len(a.cross_refs) for a in articles)
    # PTK uses very few inline X:Y. § cross-refs; structural refs are added by the indexer
    _r("AC4 inline cross-references extracted", total_xrefs >= 1, f"{total_xrefs} total inline cross-refs")

    sample = next((a for a in articles if a.article_ref == "6:130"), None)
    if sample:
        _r("AC5 hierarchy correct for 6:130",
           sample.book_num == 6 and "HATODIK" in sample.book_name,
           f"book_num={sample.book_num} book_name='{sample.book_name}'")
    else:
        _r("AC5 hierarchy correct for 6:130", False, "article 6:130 not found")

    empty = [a.article_ref for a in articles if not a.full_text.strip()]
    _r("AC6 no empty full_text", len(empty) == 0, f"{len(empty)} empty articles")

    print("\nSample article:")
    a0 = articles[0]
    print(f"  ref={a0.article_ref} title={a0.title}")
    print(f"  book={a0.book_name} paragraphs={len(a0.paragraphs)} xrefs={a0.cross_refs}")
    print("\nDone. Share results for Stage 3a review gate.")


if __name__ == "__main__":
    main()
