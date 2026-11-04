"""Unit & Integration Tests for Phase 2: Source Registry, Official Collectors, and Document Ingestion.
"""
import io
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db import SessionLocal, init_db
from app.database.repository import ResearchRepository
from app.collectors.registry import registry
from app.collectors.manual_import import ManualImportCollector
from app.collectors.chittorgarh import ChittorgarhCollector
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


def test_source_registry_listing():
    sources = registry.list_sources()
    assert len(sources) >= 3
    source_ids = [s["id"] for s in sources]
    assert "sebi_official" in source_ids
    assert "chittorgarh" in source_ids
    assert "manual_import" in source_ids

    # Tier 1 official sources
    official_sources = [s for s in sources if s["is_official"]]
    assert len(official_sources) >= 2


def test_manual_import_and_hash_deduplication(tmp_path):
    # Create sample synthetic PDF file
    sample_pdf = tmp_path / "sample_rating_report.pdf"
    sample_pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF")

    importer = ManualImportCollector()
    res1 = importer.import_local_file(sample_pdf, company_name="Test Corp", document_type="RATING_REPORT")

    assert res1.success is True
    assert res1.sha256_hash is not None
    assert len(res1.sha256_hash) == 64
    assert res1.file_path.exists()

    # Re-import same file -> should be flagged as duplicate
    res2 = importer.import_local_file(sample_pdf, company_name="Test Corp", document_type="RATING_REPORT")
    assert res2.success is True
    assert res2.is_duplicate is True
    assert res2.sha256_hash == res1.sha256_hash


def test_chittorgarh_local_discovery():
    cg = ChittorgarhCollector()
    # Discover against a known IPO from the 1000+ local dataset (e.g. Zomato, Tata, Acme)
    discovered = cg.discover("Zomato")
    if discovered:
        doc = discovered[0]
        assert doc.source_url.startswith("http")
        assert doc.tier == "tier_1_official"
        assert doc.document_type in ("RHP", "DRHP", "PROSPECTUS")


def test_api_document_endpoints(db_session):
    client = TestClient(app)
    repo = ResearchRepository(db_session)
    comp = repo.create_company("Doc Test Corp", cin="U99999KA2022PTC111111")

    # 1. List sources
    src_resp = client.get("/api/sources")
    assert src_resp.status_code == 200
    assert len(src_resp.json()) >= 3

    # 2. Upload document via manual upload API
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    upload_resp = client.post(
        f"/api/companies/{comp.id}/upload-document?document_type=ANNUAL_REPORT",
        files={"file": ("financial_statements_2026.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 200
    doc_data = upload_resp.json()
    assert doc_data["document_type"] == "ANNUAL_REPORT"
    assert len(doc_data["sha256"]) == 64
    assert doc_data["filename"] == "financial_statements_2026.pdf"

