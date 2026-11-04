"""Unit & Integration Tests for Phase 1: Company Management, Database Abstraction, and Entity Resolution.
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db import Base, SessionLocal, engine, init_db
from app.database.schema import Company, ResearchPlan, ChecklistTemplate, ChecklistExecution
from app.database.repository import ResearchRepository
from app.discovery.entity_resolver import EntityResolver
from app.main import app


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure all tables are created in SQLite test DB."""
    init_db()
    yield


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_cin_validation_and_parsing():
    valid_cin = "L64200GJ2019PLC108044"  # Realistic Indian Listed Telco CIN structure
    invalid_cin = "INVALID123"

    assert EntityResolver.is_valid_cin(valid_cin) is True
    assert EntityResolver.is_valid_cin(invalid_cin) is False

    details = EntityResolver.parse_cin_details(valid_cin)
    assert details["valid"] is True
    assert details["is_listed"] is True
    assert details["state_code"] == "GJ"
    assert details["incorporation_year"] == 2019
    assert details["company_type"] == "PLC"


def test_entity_resolver_disambiguation():
    parent = "Reliance Jio Infocomm Limited"
    subsidiary = "Jio Digital Platforms Limited"
    unrelated = "Tata Consultancy Services Limited"

    # Exact normalize
    assert EntityResolver.normalize_name("Reliance Jio Infocomm Ltd.") == "reliance jio infocomm"

    # Disambiguate related party / subsidiary
    res_sub = EntityResolver.disambiguate_relation(parent, subsidiary, "wholly owned subsidiary of Reliance Jio")
    assert res_sub["is_same_entity"] is False
    assert res_sub["relation"] == "related_party_or_subsidiary"

    # Distinct entity
    res_unrelated = EntityResolver.disambiguate_relation(parent, unrelated)
    assert res_unrelated["is_same_entity"] is False
    assert res_unrelated["relation"] == "distinct_entity"


def test_company_repository_crud(db_session):
    repo = ResearchRepository(db_session)
    comp_name = "Jio Platforms Test"
    cin = "U72900MH2019PTC333333"

    # Create company
    comp = repo.create_company(
        name=comp_name,
        legal_name="Jio Platforms Private Limited",
        cin=cin,
        industry="Telecommunications & Tech",
        sector="Information Technology",
        website="https://www.jio.com",
        incorporation_year=2019,
    )
    assert comp.id is not None
    assert comp.name == comp_name

    # Idempotent fetch
    fetched = repo.get_company_by_cin(cin)
    assert fetched is not None
    assert fetched.id == comp.id

    # Add identifiers
    ident_nse = repo.add_company_identifier(comp.id, "nse_symbol", "JIO", is_primary=True)
    assert ident_nse.id_value == "JIO"
    assert ident_nse.id_type == "nse_symbol"


import uuid

def test_research_plan_and_checklist_flow(db_session):
    repo = ResearchRepository(db_session)
    unique_cin = f"U{uuid.uuid4().int % 90000 + 10000}DL2020PTC{uuid.uuid4().int % 900000 + 100000}"
    comp = repo.create_company(name=f"Test Research Entity {uuid.uuid4().hex[:6]}", cin=unique_cin)

    # Seed 2 checklist templates
    repo.seed_checklist_template(
        template_id="TEST_PROFIT_PAT",
        category="profitability",
        question="Has the company reported positive PAT in the latest financial year?",
        weight=1.0,
        display_order=1,
    )
    repo.seed_checklist_template(
        template_id="TEST_DEBT_EQUITY",
        category="balance_sheet",
        question="Is Debt to Equity below 1.5x?",
        weight=1.0,
        display_order=2,
    )

    # Create plan
    plan = repo.create_or_get_research_plan(comp.id, "Pilot Test Plan")
    assert plan.id is not None
    assert plan.total_checks >= 2
    assert plan.status in ("pending", "in_progress")

    # Execute a checklist item
    exec_item = db_session.query(ChecklistExecution).filter_by(
        research_plan_id=plan.id, template_id="TEST_PROFIT_PAT"
    ).first()
    assert exec_item is not None

    updated = repo.update_checklist_execution(
        execution_id=exec_item.id,
        status="YES",
        result_value="Verified PAT ₹5,200 Cr",
        raw_metric_value=5200.0,
        unit="crore",
        reporting_period="FY2026",
        basis="Consolidated",
        explanation="Audited FY26 consolidated statement confirms positive PAT.",
        confidence=0.98,
    )
    assert updated.status == "YES"
    assert updated.raw_metric_value == 5200.0

    # Add atomic evidence record linked to execution
    evidence = repo.add_evidence(
        company_id=comp.id,
        document_name="Annual_Report_FY26.pdf",
        extracted_text="Profit after tax for the year ended March 31, 2026 stood at ₹5,200 crore.",
        source_url="https://example.com/reports/fy26.pdf",
        source_tier="tier_1_official",
        source_organization="Company Investor Relations",
        page_number=142,
        extracted_value=5200.0,
        unit="crore",
        reporting_period="FY2026",
        financial_basis="Consolidated",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        execution_id=exec_item.id,
    )
    assert evidence.id is not None
    linked_evidence = repo.get_evidence_for_execution(exec_item.id)
    assert len(linked_evidence) == 1
    assert linked_evidence[0].page_number == 142


def test_api_company_endpoints():
    client = TestClient(app)

    # 1. Create company via API
    payload = {
        "name": "API Pilot Energy Ltd",
        "legal_name": "API Pilot Energy Limited",
        "cin": "L40100MH2021PLC987654",
        "industry": "Renewable Energy",
        "sector": "Utilities",
        "website": "https://pilotenergy.example.com"
    }
    resp = client.post("/api/companies", json=payload)
    assert resp.status_code in (201, 200)
    data = resp.json()
    assert data["name"] == "API Pilot Energy Ltd"
    comp_id = data["id"]

    # 2. Get company detail
    get_resp = client.get(f"/api/companies/{comp_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["cin"] == "L40100MH2021PLC987654"

    # 3. Add identifier
    ident_resp = client.post(
        f"/api/companies/{comp_id}/identifiers",
        json={"id_type": "bse_code", "id_value": "543210", "is_primary": False}
    )
    assert ident_resp.status_code == 200
    assert ident_resp.json()["id_value"] == "543210"

    # 4. List companies
    list_resp = client.get(f"/api/companies?q=Pilot")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
