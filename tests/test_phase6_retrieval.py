"""Unit Tests for Phase 6: BM25, Vector Search, and Hybrid Reciprocal Rank Fusion.
"""
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.retrieval_engine.keyword_search import BM25Index
from app.retrieval_engine.vector_search import VectorIndex
from app.retrieval_engine.hybrid_retriever import HybridRetriever


@pytest.fixture
def sample_chunks():
    return [
        {
            "chunk_id": "c1",
            "page_number": 14,
            "section_name": "Basis for Offer Price",
            "text": "The issuer P/E ratio at the upper price band of ₹850 is 28.5x based on FY2026 restated EPS of ₹29.8.",
            "doc_type": "RHP",
        },
        {
            "chunk_id": "c2",
            "page_number": 88,
            "section_name": "Financial Statements",
            "text": "Consolidated Revenue from Operations for the year ended March 31, 2026 stood at ₹14,500 crore.",
            "doc_type": "RHP",
        },
        {
            "chunk_id": "c3",
            "page_number": 150,
            "section_name": "Outstanding Litigation",
            "text": "There are no criminal proceedings pending against the promoters or directors of the company.",
            "doc_type": "RHP",
        },
        {
            "chunk_id": "c4",
            "page_number": 210,
            "section_name": "Credit Rating Rationale",
            "text": "CRISIL has assigned AAA/Stable rating for the company's long-term bank loan facilities of ₹5,000 crore.",
            "doc_type": "RATING_REPORT",
        },
    ]


def test_bm25_exact_keyword_retrieval(sample_chunks):
    bm25 = BM25Index()
    bm25.add_documents(sample_chunks)

    # Search for P/E ratio
    results = bm25.search("P/E ratio price band 28.5x", top_k=2)
    assert len(results) >= 1
    top_doc = results[0]["doc"]
    assert top_doc["chunk_id"] == "c1"
    assert top_doc["page_number"] == 14

    # Search with metadata filter
    rating_results = bm25.search("credit rating loan facilities", filter_meta={"doc_type": "RATING_REPORT"})
    assert len(rating_results) == 1
    assert rating_results[0]["doc"]["chunk_id"] == "c4"


def test_vector_search_semantic_matching(sample_chunks):
    vec_index = VectorIndex(dim=64)
    vec_index.add_documents(sample_chunks)

    results = vec_index.search("company annual turnover and sales", top_k=2)
    assert len(results) >= 1
    assert results[0]["score"] > 0.0


def test_hybrid_retriever_rrf_fusion(sample_chunks):
    hybrid = HybridRetriever(rrf_k=60)
    hybrid.index_chunks(sample_chunks)

    fused = hybrid.hybrid_search("criminal cases litigation directors", top_k=3)
    assert len(fused) >= 1
    top_match = fused[0]
    assert top_match["chunk"]["chunk_id"] == "c3"
    assert top_match["page_number"] == 150
    assert top_match["section"] == "Outstanding Litigation"
    assert top_match["rrf_score"] > 0.0

