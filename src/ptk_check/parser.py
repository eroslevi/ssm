from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

BOOK_ORDINALS = {
    "ELSŐ": 1, "MÁSODIK": 2, "HARMADIK": 3, "NEGYEDIK": 4,
    "ÖTÖDIK": 5, "HATODIK": 6, "HETEDIK": 7, "NYOLCADIK": 8,
}

# Matches: BOOK:NUM. § [Title]  and  BOOK:NUM/A. § *  [Title]  and  BOOK:NUM. § *
_ARTICLE_RE  = re.compile(r'^(\d+):(\d+(?:/[A-Z])?)\.[\s]*§(?:[\s]*\*+)?[\s]*(?:\[(.+)\])?')
_CROSSREF_RE = re.compile(r'(\d+):(\d+(?:/[A-Z])?)\.\s*§')
_NUM_RE      = re.compile(r'\d+')
_PARA_RE     = re.compile(r'^\((\d+)\)\s+(.+)')
_POINT_RE    = re.compile(r'^([a-záéíóöőúüű])\)\s+(.+)', re.IGNORECASE)
_BOOK_RE     = re.compile(r'^(ELSŐ|MÁSODIK|HARMADIK|NEGYEDIK|ÖTÖDIK|HATODIK|HETEDIK|NYOLCADIK) KÖNYV$')
_PART_RE     = re.compile(r'^(ELSŐ|MÁSODIK|HARMADIK|NEGYEDIK|ÖTÖDIK|HATODIK|HETEDIK|NYOLCADIK) RÉSZ$')
_CIM_RE      = re.compile(r'^([IVXLC]+)\. CÍM$')
_FEJEZET_RE  = re.compile(r'^([IVXLC]+|\d+)\.\s+Fejezet$')


@dataclass
class ParsedArticle:
    law_id: str
    article_ref: str
    book_num: int
    article_num: int
    title: str
    full_text: str
    book_name: str
    part_name: str
    title_name: str
    chapter_name: str
    paragraphs: list = field(default_factory=list)
    cross_refs: list = field(default_factory=list)


def parse_ptk(file_path: str, law_id: str = "2013-5") -> list[ParsedArticle]:
    text = Path(file_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    articles: list[ParsedArticle] = []
    current: ParsedArticle | None = None
    current_lines: list[str] = []

    ctx_book_num  = 0
    ctx_book_name = ""
    ctx_part_name = ""
    ctx_title_name  = ""
    ctx_chapter_name = ""

    for line in lines:
        stripped = line.strip()

        m = _BOOK_RE.match(stripped)
        if m:
            ctx_book_num  = BOOK_ORDINALS[m.group(1)]
            ctx_book_name = stripped
            ctx_part_name = ctx_title_name = ctx_chapter_name = ""
            continue

        if _PART_RE.match(stripped):
            ctx_part_name = stripped
            ctx_title_name = ctx_chapter_name = ""
            continue

        if _CIM_RE.match(stripped):
            ctx_title_name = stripped
            ctx_chapter_name = ""
            continue

        if _FEJEZET_RE.match(stripped):
            ctx_chapter_name = stripped
            continue

        m = _ARTICLE_RE.match(stripped)
        if m:
            if current is not None:
                _finalise(current, current_lines)
                articles.append(current)
            book_num        = int(m.group(1))
            article_num_str = m.group(2)            # e.g. "130" or "167/A"
            article_num     = int(_NUM_RE.match(article_num_str).group())
            current = ParsedArticle(
                law_id=law_id,
                article_ref=f"{book_num}:{article_num_str}",
                book_num=book_num,
                article_num=article_num,
                title=m.group(3) or "",
                full_text="",
                book_name=ctx_book_name,
                part_name=ctx_part_name,
                title_name=ctx_title_name,
                chapter_name=ctx_chapter_name,
            )
            current_lines = [stripped]
            continue

        if current is not None and stripped:
            current_lines.append(stripped)

    if current is not None:
        _finalise(current, current_lines)
        articles.append(current)

    return articles


def _finalise(article: ParsedArticle, lines: list[str]) -> None:
    article.full_text = "\n".join(lines)

    current_para: dict | None = None
    for line in lines[1:]:
        m = _PARA_RE.match(line)
        if m:
            if current_para:
                article.paragraphs.append(current_para)
            current_para = {"num": int(m.group(1)), "text": m.group(2), "points": []}
            continue
        if current_para:
            mp = _POINT_RE.match(line)
            if mp:
                current_para["points"].append({"label": mp.group(1), "text": mp.group(2)})
            else:
                current_para["text"] += " " + line
    if current_para:
        article.paragraphs.append(current_para)

    refs: set[str] = set()
    for m in _CROSSREF_RE.finditer(article.full_text):
        ref = f"{m.group(1)}:{m.group(2)}"
        if ref != article.article_ref:
            refs.add(ref)
    article.cross_refs = sorted(refs)
