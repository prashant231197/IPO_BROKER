"""Company Management REST API Endpoints.

Provides endpoints for company registration, CIN validation, identifier tagging,
listing, and legal entity resolution.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from ..db import get_db
from ..database.repository import ResearchRepository
from ..discovery.entity_resolver import EntityResolver

router = APIRouter(prefix="/companies", tags=["Companies"])


class CompanyCreateIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=256, description="Company trading or brand name")
    legal_name: str | None = Field(None, max_length=512, description="Full registered legal entity name")
    cin: str | None = Field(None, max_length=21, description="Indian MCA Corporate Identity Number")
    industry: str | None = Field(None, max_length=128)
    sector: str | None = Field(None, max_length=128)
    website: str | None = Field(None, max_length=512)
    description: str | None = None
    incorporation_year: int | None = Field(None, ge=1800, le=2100)


class IdentifierIn(BaseModel):
    id_type: str = Field(..., max_length=32, description="cin, nse_symbol, bse_code, isin, alias")
    id_value: str = Field(..., min_length=1, max_length=128)
    source: str | None = "manual"
    is_primary: bool = False


@router.post("", status_code=201)
def create_company(body: CompanyCreateIn, db: DbSession = Depends(get_db)) -> dict[str, Any]:
    """Register or lookup a company by Name / CIN."""
    repo = ResearchRepository(db)
    if body.cin and not EntityResolver.is_valid_cin(body.cin):
        raise HTTPException(400, f"Invalid Indian CIN format: '{body.cin}'. Must be 21 characters matching MCA structure.")

    cin_info = EntityResolver.parse_cin_details(body.cin) if body.cin else {}
    inc_year = body.incorporation_year or cin_info.get("incorporation_year")

    company = repo.create_company(
        name=body.name,
        legal_name=body.legal_name,
        cin=body.cin,
        industry=body.industry,
        sector=body.sector,
        website=body.website,
        description=body.description,
        incorporation_year=inc_year,
    )
    if body.cin:
        repo.add_company_identifier(company.id, "cin", body.cin, source="mca", is_primary=True)

    return {
        "id": company.id,
        "name": company.name,
        "legal_name": company.legal_name,
        "cin": company.cin,
        "industry": company.industry,
        "sector": company.sector,
        "website": company.website,
        "incorporation_year": company.incorporation_year,
        "status": company.status,
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }


@router.get("")
def list_companies(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, description="Search term for company name or CIN"),
    db: DbSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List or search registered companies."""
    repo = ResearchRepository(db)
    if q:
        match = repo.get_company_by_cin(q) or repo.get_company_by_name(q)
        if match:
            return [{
                "id": match.id,
                "name": match.name,
                "legal_name": match.legal_name,
                "cin": match.cin,
                "industry": match.industry,
                "sector": match.sector,
                "status": match.status,
                "created_at": match.created_at.isoformat() if match.created_at else None,
            }]
    companies = repo.list_companies(limit=limit, offset=offset)
    return [{
        "id": c.id,
        "name": c.name,
        "legal_name": c.legal_name,
        "cin": c.cin,
        "industry": c.industry,
        "sector": c.sector,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    } for c in companies]


@router.get("/{company_id}")
def get_company_detail(company_id: str, db: DbSession = Depends(get_db)) -> dict[str, Any]:
    """Retrieve full company details including identifiers and research plans."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    return {
        "id": company.id,
        "name": company.name,
        "legal_name": company.legal_name,
        "cin": company.cin,
        "industry": company.industry,
        "sector": company.sector,
        "website": company.website,
        "incorporation_year": company.incorporation_year,
        "description": company.description,
        "is_listed": company.is_listed,
        "status": company.status,
        "identifiers": [{
            "id": ident.id,
            "type": ident.id_type,
            "value": ident.id_value,
            "source": ident.source,
            "is_primary": ident.is_primary,
        } for ident in company.identifiers],
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }


@router.post("/{company_id}/identifiers")
def add_identifier(company_id: str, body: IdentifierIn, db: DbSession = Depends(get_db)) -> dict[str, Any]:
    """Attach stock ticker, CIN, ISIN, or alias to a company."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    ident = repo.add_company_identifier(
        company_id=company.id,
        id_type=body.id_type,
        id_value=body.id_value,
        source=body.source,
        is_primary=body.is_primary,
    )
    return {
        "id": ident.id,
        "company_id": ident.company_id,
        "id_type": ident.id_type,
        "id_value": ident.id_value,
        "is_primary": ident.is_primary,
    }

