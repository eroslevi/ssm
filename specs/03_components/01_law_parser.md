# Component Spec — LawParser

**Stage:** 2a | **Status:** APPROVED

---

## Responsibility

Parses the PTK plain text file into a list of structured article dicts.
Extracts the full hierarchy, paragraph sub-structure, and cross-references.

---

## Input

Plain text file (`ptk.txt`). Structure observed in the actual file:

```
ELSŐ KÖNYV                          ← Book heading (uppercase ordinal + KÖNYV)
BEVEZETŐ RENDELKEZÉSEK              ← Book subtitle

ELSŐ RÉSZ                           ← Part (RÉSZ)
I. CÍM                              ← Title (CÍM) or Fejezet (chapter)

1:1. § [A törvény hatálya]          ← Article: BOOK:NUM. § [TITLE]

(1) szöveg...                       ← Paragraph
(2) szöveg...
  a) pont...                        ← Sub-point
```

Cross-references appear inline in body text: `3:167. § (2) bekezdése`

---

## Output

```python
@dataclass
class ParsedArticle:
    law_id: str            # "2013-5"
    article_ref: str       # "6:130"
    book_num: int          # 6
    article_num: int       # 130
    title: str             # "Kártérítési kötelezettség"
    full_text: str         # complete article text (all paragraphs joined)
    book_name: str         # "HATODIK KÖNYV"
    part_name: str         # "MÁSODIK RÉSZ"   (or "" if none)
    title_name: str        # "III. CÍM"       (or "" if none)
    chapter_name: str      # "II. Fejezet"    (or "" if none)
    paragraphs: list[dict] # [{"num": 1, "text": "..."}, ...]
    cross_refs: list[str]  # ["6:215", "3:42"] — article_refs found in body
```

---

## Parsing Logic

Three regex patterns cover the entire file:

```python
ARTICLE_RE  = re.compile(r'^(\d+):(\d+)\. § \[(.+)\]$')
CROSSREF_RE = re.compile(r'(\d+):(\d+)\. §')
PARA_RE     = re.compile(r'^\((\d+)\)\s+(.+)')
```

State machine reads line-by-line:
1. Update current Book/Part/Title/Chapter when heading lines are seen
2. On ARTICLE_RE match: save previous article, start new one
3. Accumulate paragraph lines and sub-points into current article
4. After parsing: scan `full_text` for CROSSREF_RE to extract cross_refs

---

## Acceptance Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| AC1 | All 1,498 articles parsed | `len(articles) == 1498` |
| AC2 | All 8 books present | `{a.book_num for a in articles} == {1..8}` |
| AC3 | Article refs unique within law | no duplicate `article_ref` values |
| AC4 | Cross-references extracted | at least 200 cross-refs found across corpus |
| AC5 | Hierarchy correctly assigned | article `6:130` has `book_num=6`, `book_name="HATODIK KÖNYV"` |
| AC6 | No empty full_text | all articles have `len(full_text) > 0` |
