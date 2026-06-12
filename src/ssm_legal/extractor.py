from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import joblib
import torch
from sklearn.feature_extraction.text import TfidfVectorizer

if TYPE_CHECKING:
    from ssm_legal.engine import SSMEngine

_PASSAGE_CHARS = 800
_STRIDE_CHARS = 200
_TOP_K = 5
_MAX_LAW_TOKENS = 2048


@dataclass
class Violation:
    statement_excerpt: str
    law_excerpt: str
    explanation: str


class ComplianceExtractor:

    @staticmethod
    def build_index(laws_path: str, index_path: str) -> None:
        """Build TF-IDF index over the law corpus and save to disk. Called once during ingest."""
        text = Path(laws_path).read_text(encoding="utf-8")
        passages: list[str] = []
        for i in range(0, max(1, len(text) - _PASSAGE_CHARS + 1), _STRIDE_CHARS):
            p = text[i : i + _PASSAGE_CHARS]
            if p.strip():
                passages.append(p)
        if not passages or passages[-1] != text[-_PASSAGE_CHARS:]:
            tail = text[-_PASSAGE_CHARS:] if len(text) >= _PASSAGE_CHARS else text
            if tail.strip():
                passages.append(tail)

        vectorizer = TfidfVectorizer(max_features=50_000, sublinear_tf=True)
        matrix = vectorizer.fit_transform(passages)
        joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "passages": passages}, index_path)
        print(f"  index: {len(passages)} passages, {matrix.shape[1]} features → {index_path}")

    def __init__(self, index_path: str, engine: "SSMEngine", tokenizer, threshold_std: float = 2.0):
        saved = joblib.load(index_path)
        self.vectorizer = saved["vectorizer"]
        self.tfidf_matrix = saved["matrix"]
        self.passages = saved["passages"]
        self.engine = engine
        self.tokenizer = tokenizer
        self.threshold_std = threshold_std

    def extract(self, statement: str) -> list[Violation]:
        """Retrieve relevant law passages, run Mamba over [law_context | statement], return violations."""
        # 1. Retrieve top-k law passages by TF-IDF similarity to statement
        stmt_vec = self.vectorizer.transform([statement])
        scores = (self.tfidf_matrix @ stmt_vec.T).toarray().flatten()
        top_idx = scores.argsort()[-_TOP_K:][::-1]
        law_passages = [self.passages[i] for i in top_idx]

        # 2. Tokenize separately so statement_start is exact
        law_token_ids: list[int] = []
        for p in law_passages:
            ids = self.tokenizer.encode(p, add_special_tokens=False)
            if len(law_token_ids) + len(ids) > _MAX_LAW_TOKENS:
                remaining = _MAX_LAW_TOKENS - len(law_token_ids)
                law_token_ids.extend(ids[:remaining])
                break
            law_token_ids.extend(ids)

        stmt_token_ids: list[int] = self.tokenizer.encode(statement, add_special_tokens=False)
        statement_start = len(law_token_ids)
        combined = torch.tensor(law_token_ids + stmt_token_ids, dtype=torch.long)

        # 3. Single forward pass through SSM
        log_probs = self.engine.forward(combined)  # (n_combined, vocab_size)

        # 4. Cross-entropy for statement tokens only
        n_stmt = len(stmt_token_ids)
        stmt_log_probs = log_probs[statement_start : statement_start + n_stmt]
        ce = -stmt_log_probs[range(n_stmt), stmt_token_ids]

        # 5. Flag tokens above mean + k·std
        if n_stmt < 2 or ce.std() < 1e-6:
            return []
        threshold = ce.mean() + self.threshold_std * ce.std()
        flagged = (ce > threshold).nonzero(as_tuple=True)[0].tolist()

        # 6. Merge adjacent flagged tokens into spans, build Violation objects
        violations: list[Violation] = []
        for span_start, span_end in _merge_spans(flagged):
            excerpt = self.tokenizer.decode(stmt_token_ids[span_start : span_end + 1]).strip()
            if not excerpt:
                continue
            span_vec = self.vectorizer.transform([excerpt])
            span_scores = (self.tfidf_matrix @ span_vec.T).toarray().flatten()
            best = self.passages[span_scores.argmax()]
            violations.append(Violation(
                statement_excerpt=excerpt,
                law_excerpt=best[:300].strip(),
                explanation=(
                    f"The statement's claim that '{excerpt}' "
                    f"may conflict with the legal provision: '{best[:150].strip()}'."
                ),
            ))
        return violations


def _merge_spans(indices: list[int]) -> list[tuple[int, int]]:
    if not indices:
        return []
    spans, start, end = [], indices[0], indices[0]
    for i in indices[1:]:
        if i == end + 1:
            end = i
        else:
            spans.append((start, end))
            start = end = i
    spans.append((start, end))
    return spans
