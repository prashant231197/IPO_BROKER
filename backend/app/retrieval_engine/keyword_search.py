"""BM25 & Inverted Index Keyword Retrieval Engine (Pure Python / Termux Compatible).

Provides exact keyword and term matching for:
- Financial figures, case numbers, promoter names, accounting terms
- Works with zero external C++ dependencies, 100% portable on Android Termux.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size: int = 0
        self.avg_doc_len: float = 0.0
        self.doc_lens: list[int] = []
        self.doc_term_freqs: list[Counter] = []
        self.doc_records: list[dict[str, Any]] = []
        self.df: Counter = Counter()

    def tokenize(self, text: str) -> list[str]:
        if not text:
            return []
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        return [w for w in cleaned.split() if len(w) > 1]

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        """Indexes a batch of document chunk dicts (each having 'text', 'page_number', 'chunk_id', etc.)."""
        for doc in documents:
            text = doc.get("text", "")
            tokens = self.tokenize(text)
            term_freq = Counter(tokens)
            doc_len = len(tokens)

            self.doc_records.append(doc)
            self.doc_term_freqs.append(term_freq)
            self.doc_lens.append(doc_len)

            for term in term_freq:
                self.df[term] += 1

        self.corpus_size = len(self.doc_records)
        self.avg_doc_len = (sum(self.doc_lens) / self.corpus_size) if self.corpus_size > 0 else 0.0

    def search(self, query: str, top_k: int = 5, filter_meta: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Scores indexed chunks using BM25 with optional metadata filtering."""
        if not self.corpus_size:
            return []

        q_tokens = self.tokenize(query)
        if not q_tokens:
            return []

        scores: list[float] = [0.0] * self.corpus_size

        for term in q_tokens:
            if term not in self.df:
                continue
            df_t = self.df[term]
            idf = math.log((self.corpus_size - df_t + 0.5) / (df_t + 0.5) + 1.0)

            for i in range(self.corpus_size):
                tf = self.doc_term_freqs[i].get(term, 0)
                if tf == 0:
                    continue
                doc_len = self.doc_lens[i]
                num = tf * (self.k1 + 1.0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len)) if self.avg_doc_len > 0 else 1.0
                scores[i] += idf * (num / denom)

        ranked = []
        for i, score in enumerate(scores):
            if score <= 0.0:
                continue
            doc = self.doc_records[i]

            # Apply metadata filters if specified
            if filter_meta:
                match = True
                for k, v in filter_meta.items():
                    if doc.get(k) != v and doc.get("metadata", {}).get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            ranked.append({
                "score": round(score, 4),
                "doc": doc,
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]

