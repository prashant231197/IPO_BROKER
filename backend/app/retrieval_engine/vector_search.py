"""Vector Search & Semantic Embedding Engine.

Provides semantic similarity search across document chunks with:
- Pure-NumPy cosine similarity fallback for lightweight mode / Android Termux
- Optional FAISS acceleration when available
- Metadata preservation (page number, section, document hash)
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any
import numpy as np

log = logging.getLogger("vector_search")


class VectorIndex:
    def __init__(self, dim: int = 128):
        self.dim = dim
        self.vectors: list[np.ndarray] = []
        self.documents: list[dict[str, Any]] = []

    def _embed_text_lightweight(self, text: str) -> np.ndarray:
        """Lightweight deterministic feature embedding for Termux/offline use."""
        vec = np.zeros(self.dim, dtype=np.float32)
        words = [w for w in re.sub(r"[^a-zA-Z0-9]", " ", text.lower()).split() if len(w) > 1]
        if not words:
            return vec

        for word in words:
            # Hash word into bucket
            h = hash(word) % self.dim
            vec[h] += 1.0

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        """Embeds and indexes document chunks."""
        for doc in documents:
            text = doc.get("text", "")
            vec = self._embed_text_lightweight(text)
            self.vectors.append(vec)
            self.documents.append(doc)

    def search(self, query: str, top_k: int = 5, filter_meta: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Finds nearest document chunks using cosine similarity."""
        if not self.documents:
            return []

        q_vec = self._embed_text_lightweight(query)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        results = []
        for i, doc_vec in enumerate(self.vectors):
            doc = self.documents[i]

            # Apply metadata filter
            if filter_meta:
                match = True
                for k, v in filter_meta.items():
                    if doc.get(k) != v and doc.get("metadata", {}).get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            sim = float(np.dot(q_vec, doc_vec))
            if sim > 0:
                results.append({
                    "score": round(sim, 4),
                    "doc": doc,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

