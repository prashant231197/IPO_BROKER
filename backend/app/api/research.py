"""Research Plan & Checklist Engine REST API Endpoints.

Provides endpoints to trigger research plans, inspect checklist progress,
and review atomic evidence citations.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..db import get_db
from ..database.repository import ResearchRepository
from ..database.schema import ChecklistExecution, ChecklistTemplate, ResearchPlan
from ..research_engine.checklist_executor import ChecklistExecutor
from ..research_engine.checklist_templates import seed_master_templates

router = APIRouter(prefix="/companies/{company_id}", tags=["Research & Checklists"])


class ManualVerificationIn(BaseModel):
    status: str = Field(..., description="YES, NO, PARTIAL, NOT AVAILABLE, CONFLICT, NOT APPLICABLE")
    result_value: str | None = None
    explanation: str | None = None
    source_url: str | None = None
    page_number: int | None = None
    verification_notes: str | None = None


@router.post("/research/start")
def start_company_research(
    company_id: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Generates the master 26-point research plan and executes automated verification."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    seed_master_templates(repo)
    plan = repo.create_or_get_research_plan(company.id)
    executor = ChecklistExecutor(db)
    result = executor.execute_plan(plan.id)
    return result


@router.get("/research/status")
def get_research_status(
    company_id: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Returns research plan completion metrics and status breakdown."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    plan = repo.get_latest_plan_for_company(company.id)
    if not plan:
        return {
            "status": "NOT_STARTED",
            "progress": 0.0,
            "total_checks": 26,
            "completed_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "missing_checks": 26,
            "conflict_checks": 0,
        }

    return {
        "plan_id": plan.id,
        "status": plan.status,
        "progress": plan.progress,
        "total_checks": plan.total_checks,
        "completed_checks": plan.completed_checks,
        "passed_checks": plan.passed_checks,
        "failed_checks": plan.failed_checks,
        "missing_checks": plan.missing_checks,
        "conflict_checks": plan.conflict_checks,
        "started_at": plan.started_at.isoformat() if plan.started_at else None,
        "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
    }


@router.get("/checklist")
def get_company_checklist(
    company_id: str,
    db: DbSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves all checklist execution items with their verified result, explanation, and evidence."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    plan = repo.get_latest_plan_for_company(company.id)
    if not plan:
        # Return empty template structure
        templates = repo.get_all_templates()
        if not templates:
            seed_master_templates(repo)
            templates = repo.get_all_templates()
        return [{
            "execution_id": None,
            "template_id": t.id,
            "category": t.category,
            "question": t.question,
            "is_mandatory": t.is_mandatory,
            "status": "PENDING",
            "result_value": None,
            "explanation": "Research not yet initiated.",
            "evidence_count": 0,
        } for t in templates]

    items = db.execute(
        select(ChecklistExecution, ChecklistTemplate)
        .join(ChecklistTemplate, ChecklistTemplate.id == ChecklistExecution.template_id)
        .where(ChecklistExecution.research_plan_id == plan.id)
        .order_by(ChecklistTemplate.display_order.asc())
    ).all()

    return [{
        "execution_id": ex.id,
        "template_id": tmpl.id,
        "category": tmpl.category,
        "question": tmpl.question,
        "is_mandatory": tmpl.is_mandatory,
        "weight": tmpl.weight,
        "status": ex.status,
        "result_value": ex.result_value,
        "raw_metric_value": ex.raw_metric_value,
        "unit": ex.unit,
        "reporting_period": ex.reporting_period,
        "basis": ex.basis,
        "explanation": ex.explanation,
        "evidence_count": ex.evidence_count,
        "confidence": ex.confidence,
        "verified_at": ex.verified_at.isoformat() if ex.verified_at else None,
    } for ex, tmpl in items]


@router.get("/checklist/{item_id}")
def get_checklist_item_detail(
    company_id: str,
    item_id: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves single checklist item details with all linked evidence citations."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    item = db.get(ChecklistExecution, item_id)
    if not item:
        # Check by template_id
        plan = repo.get_latest_plan_for_company(company.id)
        if plan:
            item = db.execute(
                select(ChecklistExecution).where(
                    ChecklistExecution.research_plan_id == plan.id,
                    ChecklistExecution.template_id == item_id
                )
            ).scalar_one_or_none()
    if not item:
        raise HTTPException(404, f"Checklist item '{item_id}' not found.")

    tmpl = db.get(ChecklistTemplate, item.template_id)
    evidence_records = repo.get_evidence_for_execution(item.id)

    return {
        "execution_id": item.id,
        "template_id": tmpl.id if tmpl else None,
        "category": tmpl.category if tmpl else None,
        "question": tmpl.question if tmpl else None,
        "status": item.status,
        "result_value": item.result_value,
        "raw_metric_value": item.raw_metric_value,
        "unit": item.unit,
        "reporting_period": item.reporting_period,
        "basis": item.basis,
        "explanation": item.explanation,
        "evidence": [{
            "id": ev.id,
            "document_name": ev.document_name,
            "source_url": ev.source_url,
            "source_tier": ev.source_tier,
            "source_organization": ev.source_organization,
            "page_number": ev.page_number,
            "section_name": ev.section_name,
            "extracted_text": ev.extracted_text,
            "reporting_period": ev.reporting_period,
            "financial_basis": ev.financial_basis,
            "sha256_hash": ev.sha256_hash,
        } for ev in evidence_records],
    }

