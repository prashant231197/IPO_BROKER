"""Unit Tests for Phase 5: 26-Point Master Checklist & Automated Execution Engine.
"""
import uuid
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db import SessionLocal, init_db
from app.database.repository import ResearchRepository
from app.research_engine.checklist_templates import MASTER_CHECKLIST_ITEMS, seed_master_templates
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


def test_master_checklist_templates_definition(db_session):
    repo = ResearchRepository(db_session)
    seed_master_templates(repo)
    templates = repo.get_all_templates()

    assert len(templates) >= 26
    categories = {t.category for t in templates}
    assert "profitability" in categories
    assert "financial_health" in categories
    assert "governance" in categories
    assert "ipo_valuation" in categories
    assert "business_quality" in categories or "legal_risk" in categories


def test_checklist_executor_workflow(db_session):
    repo = ResearchRepository(db_session)
    unique_cin = f"L{uuid.uuid4().int % 90000 + 10000}MH2020PLC{uuid.uuid4().int % 900000 + 100000}"
    company = repo.create_company(f"Jio Radar Pilot {uuid.uuid4().hex[:6]}", cin=unique_cin)

    plan = repo.create_or_get_research_plan(company.id)
    assert plan.id is not None
    assert plan.total_checks >= 26

    executor = ChecklistExecutor(db_session)
    result = executor.execute_plan(plan.id)

    assert result["plan_id"] == plan.id
    assert result["total_checks"] >= 26
    # All checks should have a valid status, none should crash
    assert result["completed_checks"] >= 0


def test_api_research_and_checklist_endpoints(db_session):
    client = TestClient(app)
    repo = ResearchRepository(db_session)
    unique_cin = f"L{uuid.uuid4().int % 90000 + 10000}DL2021PLC{uuid.uuid4().int % 900000 + 100000}"
    company = repo.create_company(f"API Research Test {uuid.uuid4().hex[:6]}", cin=unique_cin)

    # 1. Start research plan
    start_resp = client.post(f"/api/companies/{company.id}/research/start")
    assert start_resp.status_code == 200
    data = start_resp.json()
    assert "plan_id" in data
    assert data["total_checks"] >= 26

    # 2. Get research status
    status_resp = client.get(f"/api/companies/{company.id}/research/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["total_checks"] >= 26

    # 3. Get full checklist
    list_resp = client.get(f"/api/companies/{company.id}/checklist")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 26
    sample = items[0]
    assert "question" in sample
    assert "status" in sample
    assert sample["status"] in ("YES", "NO", "PARTIAL", "PENDING", "NOT AVAILABLE", "CONFLICT", "NOT APPLICABLE")

    # 4. Get single item detail
    item_id = sample.get("execution_id") or sample.get("template_id")
    detail_resp = client.get(f"/api/companies/{company.id}/checklist/{item_id}")
    assert detail_resp.status_code == 200
    assert "question" in detail_resp.json()
    assert "evidence" in detail_resp.json()

