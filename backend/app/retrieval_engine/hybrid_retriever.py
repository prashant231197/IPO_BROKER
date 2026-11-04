"""Hybrid Search & Reciprocal Rank Fusion (RRF) Retrieval Engine.

Combines:
1. Structured SQL queries (exact fiscal metrics, revenues, borrowings)
2. BM25 Keyword Search (exact financial terms, promoter names, litigation)
3. Vector Semantic Search (meaning-based contextual passages)
4. Metadata Filters (company_id, reporting_period, document_type, source_tier)
"""
from __future__ import annotations

import logging
from typing import Any

from .keyword_search import BM25Index
from .vector_search import VectorIndex

log = logging.getLogger("hybrid_retriever")


class HybridRetriever:
    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k
        self.bm25_index = BM25Index()
        self.vector_index = VectorIndex()
        self.indexed_chunk_count = 0

    def index_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """Indexes chunks across both BM25 and Vector indices simultaneously."""
        self.bm25_index.add_documents(chunks)
        self.vector_index.add_documents(chunks)
        self.indexed_chunk_count += len(chunks)

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filter_meta: dict[str, Any] | None = None,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Executes BM25 and Vector search in parallel and fuses results using Reciprocal Rank Fusion."""
        if not self.indexed_chunk_count:
            return []

        # 1. BM25 Search
        bm25_results = self.bm25_index.search(query, top_k=top_k * 2, filter_meta=filter_meta)

        # 2. Vector Search
        vector_results = self.vector_index.search(query, top_k=top_k * 2, filter_meta=filter_meta)

        # 3. Reciprocal Rank Fusion
        rrf_scores: dict[str, float] = {}
        doc_map: dict[str, dict[str, Any]] = {}

        for rank, item in enumerate(bm25_results):
            doc = item["doc"]
            doc_id = doc.get("chunk_id") or str(id(doc))
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + bm25_weight * (1.0 / (self.rrf_k + rank + 1))

        for rank, item in enumerate(vector_results):
            doc = item["doc"]
            doc_id = doc.get("chunk_id") or str(id(doc))
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + vector_weight * (1.0 / (self.rrf_k + rank + 1))

        # Sort by combined RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda did: rrf_scores[did], reverse=True)

        fused = []
        for did in sorted_ids[:top_k]:
            fused.append({
                "rrf_score": round(rrf_scores[did], 5),
                "chunk": doc_map[did],
                "page_number": doc_map[did].get("page_number"),
                "section": doc_map[did].get("section_name"),
            })

        return fused

