"""Unit Tests for Phase 7 & 8: Evidence Verification, Company Scoring Engine & IPO Valuation Score.
"""
import uuid
from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db import SessionLocal, init_db
from app.database.repository import ResearchRepository
from app.evidence_engine.source_validator import SourceValidator
from app.scoring_engine.company_score import CompanyScoreEngine
from app.scoring_engine.valuation_score import IPOValuationScoreEngine
from app.research_engine.checklist_templates import seed_master_templates
from app.research_engine.checklist_executor import ChecklistExecutor
from app.main import app


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()
    yield


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_source_validator_tiers_and_conflicts():
    # Tier 1 valid
    rep1 = SourceValidator.validate_evidence(
        evidence_tier="tier_1_official",
        financial_basis="Consolidated",
        expected_basis="Consolidated",
    )
    assert rep1.is_valid is True
    assert rep1.tier_weight == 1.0

    # Tier 4 commentary rejected
    rep4 = SourceValidator.validate_evidence(
        evidence_tier="tier_4_commentary",
        financial_basis="Consolidated",
    )
    assert rep4.is_valid is False
    assert rep4.tier_weight == 0.0

    # Conflict detection (>5% variance)
    assert SourceValidator.detect_cross_source_conflict([100.0, 108.0]) is True
    assert SourceValidator.detect_cross_source_conflict([100.0, 101.5]) is False


def test_company_scoring_engine_coverage_gates():
    # 1. Incomplete/sparse checks -> INSUFFICIENT_EVIDENCE
    sparse_items = [
        {"category": "profitability", "status": "NOT AVAILABLE", "is_mandatory": True},
        {"category": "financial_health", "status": "PENDING", "is_mandatory": True},
    ]
    res_sparse = CompanyScoreEngine.calculate_score(sparse_items)
    assert res_sparse.score_status == "INSUFFICIENT_EVIDENCE"
    assert res_sparse.company_quality_score is None

    # 2. Rich verified checks -> FINAL score
    rich_items = []
    for cat in ("profitability", "financial_health", "governance", "business_quality", "legal_risk"):
        for _ in range(4):
            rich_items.append({"category": cat, "status": "YES", "is_mandatory": True})
    res_rich = CompanyScoreEngine.calculate_score(rich_items)
    assert res_rich.score_status == "FINAL"
    assert res_rich.company_quality_score is not None
    assert 80.0 <= res_rich.company_quality_score <= 100.0


def test_ipo_valuation_scoring():
    # Attractive IPO deal
    res_attr = IPOValuationScoreEngine.calculate_valuation_score(
        issue_details={"fresh_issue_cr": 800.0, "ofs_cr": 200.0, "pe_ratio": 22.0},
        peer_median_pe=30.0,
    )
    assert res_attr.valuation_call in ("ATTRACTIVE", "REASONABLE")
    assert res_attr.fresh_issue_pct == 80.0
    assert res_attr.valuation_score >= 60.0


def test_api_scoring_endpoints(db_session):
    client = TestClient(app)
    repo = ResearchRepository(db_session)
    unique_cin = f"L{uuid.uuid4().int % 90000 + 10000}GJ2022PLC{uuid.uuid4().int % 900000 + 100000}"
    comp = repo.create_company(f"Scoring API Test {uuid.uuid4().hex[:6]}", cin=unique_cin)

    # Start research plan first
    client.post(f"/api/companies/{comp.id}/research/start")

    # Calculate score
    calc_resp = client.post(f"/api/companies/{comp.id}/scores/calculate")
    assert calc_resp.status_code == 200
    score_data = calc_resp.json()
    assert "score_status" in score_data
    assert "breakdown" in score_data

    # Fetch latest score
    get_resp = client.get(f"/api/companies/{comp.id}/scores")
    assert get_resp.status_code == 200
    assert get_resp.json()["company_id"] == comp.id

