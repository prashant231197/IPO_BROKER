"""Document Discovery & Ingestion REST API Endpoints.

Provides endpoints for multi-source document discovery, download, manual file upload,
and document registry inspection.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession
import pymupdf

from ..config import MAX_UPLOAD_MB, RAW_DOCS_DIR
from ..db import get_db
from ..database.repository import ResearchRepository
from ..collectors.registry import registry
from ..models import Document

router = APIRouter(tags=["Documents & Sources"])


class IngestUrlIn(BaseModel):
    source_url: str = Field(..., description="HTTP URL of the PDF document to ingest")
    title: str = Field(..., description="Document title or description")
    document_type: str = Field("RHP", description="RHP, DRHP, ANNUAL_REPORT, PROSPECTUS")
    source_name: str | None = "Web Download"
    source_tier: str = "tier_1_official"


@router.get("/sources")
def list_data_sources() -> list[dict[str, Any]]:
    """List all registered data source connectors and their priority tier."""
    return registry.list_sources()


@router.post("/companies/{company_id}/discover")
def discover_company_documents(
    company_id: str,
    db: DbSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Run multi-source discovery across SEBI, Chittorgarh, and local archives."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    docs = registry.discover_all(company.name, cin=company.cin)
    return [{
        "title": d.title,
        "source_name": d.source_name,
        "source_url": d.source_url,
        "document_type": d.document_type,
        "published_date": d.published_date,
        "tier": d.tier,
        "metadata": d.metadata,
    } for d in docs]


@router.post("/companies/{company_id}/ingest-url")
def ingest_document_by_url(
    company_id: str,
    body: IngestUrlIn,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Downloads an official document from URL, verifies SHA-256 hash and page count."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    collector = registry.get("sebi_official") or registry.get("manual_import")
    result = collector.download_file(body.source_url)
    if not result.success:
        raise HTTPException(502, f"Failed to download document: {result.error}")

    # Inspect page count with pymupdf
    page_count = 0
    try:
        doc_fitz = pymupdf.open(result.file_path)
        page_count = len(doc_fitz)
        doc_fitz.close()
    except Exception:
        page_count = 1

    # Persist in legacy Document table for pipeline compatibility
    doc = Document(
        filename=Path(result.file_path).name,
        stored_path=str(result.file_path),
        doc_type=body.document_type,
        page_count=page_count,
        file_size=result.file_size_bytes,
        sha256=result.sha256_hash,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "stored_path": doc.stored_path,
        "document_type": doc.doc_type,
        "sha256": doc.sha256,
        "page_count": doc.page_count,
        "file_size_bytes": doc.file_size,
        "is_duplicate": result.is_duplicate,
    }


@router.post("/companies/{company_id}/upload-document")
def upload_company_document(
    company_id: str,
    document_type: str = Query("ANNUAL_REPORT", description="RHP, DRHP, ANNUAL_REPORT, RATING_REPORT"),
    file: UploadFile = File(...),
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Uploads a local PDF directly for a company (manual fallback)."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    sha = hashlib.sha256()
    size = 0
    temp_path = RAW_DOCS_DIR / f"temp_{file.filename}"
    with open(temp_path, "wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                temp_path.unlink(missing_ok=True)
                raise HTTPException(413, f"File exceeds {MAX_UPLOAD_MB} MB limit.")
            sha.update(chunk)
            out.write(chunk)

    hex_hash = sha.hexdigest()
    final_path = RAW_DOCS_DIR / f"{hex_hash}.pdf"
    if final_path.exists():
        temp_path.unlink(missing_ok=True)
    else:
        temp_path.rename(final_path)

    try:
        doc_fitz = pymupdf.open(final_path)
        page_count = len(doc_fitz)
        doc_fitz.close()
    except Exception:
        page_count = 1

    doc = Document(
        filename=file.filename,
        stored_path=str(final_path),
        doc_type=document_type.upper(),
        page_count=page_count,
        file_size=size,
        sha256=hex_hash,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "sha256": doc.sha256,
        "page_count": doc.page_count,
        "document_type": doc.doc_type,
        "stored_path": doc.stored_path,
        "file_size": doc.file_size,
    }

