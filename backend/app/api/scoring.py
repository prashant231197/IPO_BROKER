"""Company & IPO Valuation Scoring REST API Endpoints.

Provides endpoints to trigger dual scoring, retrieve category breakdowns,
penalties, and evidence coverage metrics.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..db import get_db
from ..database.repository import ResearchRepository
from ..database.schema import ChecklistExecution, ChecklistTemplate, CompanyScoreRecord
from ..scoring_engine.company_score import CompanyScoreEngine
from ..scoring_engine.valuation_score import IPOValuationScoreEngine

router = APIRouter(prefix="/companies/{company_id}", tags=["Scoring"])


@router.get("/scores")
def get_company_scores(
    company_id: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve the latest Company Quality Score and IPO Valuation Score."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    score_rec = repo.get_latest_score_for_company(company.id)
    if not score_rec:
        return {
            "company_id": company.id,
            "company_name": company.name,
            "score_status": "NOT_SCORED",
            "company_quality_score": None,
            "ipo_valuation_score": None,
            "research_coverage_pct": 0.0,
            "evidence_quality_score": 0.0,
            "breakdown": {},
            "warnings": ["Research and checklist execution required before calculating scores."],
        }

    return {
        "company_id": company.id,
        "company_name": company.name,
        "score_status": score_rec.score_status,
        "company_quality_score": score_rec.company_quality_score,
        "ipo_valuation_score": score_rec.ipo_valuation_score,
        "research_coverage_pct": score_rec.research_coverage_pct,
        "evidence_quality_score": score_rec.evidence_quality_score,
        "breakdown": score_rec.breakdown_json,
        "penalties": score_rec.penalties_json,
        "warnings": score_rec.warnings_json,
        "calculated_at": score_rec.calculated_at.isoformat() if score_rec.calculated_at else None,
    }


@router.post("/scores/calculate")
def calculate_scores(
    company_id: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Runs rule-based scoring calculation against verified checklist items."""
    repo = ResearchRepository(db)
    company = repo.get_company(company_id)
    if not company:
        raise HTTPException(404, f"Company '{company_id}' not found.")

    plan = repo.get_latest_plan_for_company(company.id)
    if not plan:
        raise HTTPException(400, "Research plan must be started and executed before scoring.")

    # 1. Fetch executed checklist items
    items = db.execute(
        select(ChecklistExecution, ChecklistTemplate)
        .join(ChecklistTemplate, ChecklistTemplate.id == ChecklistExecution.template_id)
        .where(ChecklistExecution.research_plan_id == plan.id)
    ).all()

    checklist_dicts = []
    issue_details = {}
    for ex, tmpl in items:
        checklist_dicts.append({
            "id": ex.id,
            "template_id": tmpl.id,
            "category": tmpl.category,
            "status": ex.status,
            "is_mandatory": tmpl.is_mandatory,
            "weight": tmpl.weight,
            "raw_metric_value": ex.raw_metric_value,
        })
        if tmpl.id == "CHK_IPO_FRESH_VS_OFS" and ex.raw_metric_value:
            issue_details["fresh_issue_cr"] = ex.raw_metric_value
        elif tmpl.id == "CHK_IPO_PE_RATIO" and ex.raw_metric_value:
            issue_details["pe_ratio"] = ex.raw_metric_value

    # 2. Calculate Company Quality Score
    quality_res = CompanyScoreEngine.calculate_score(checklist_dicts)

    # 3. Calculate IPO Valuation Score
    val_res = IPOValuationScoreEngine.calculate_valuation_score(issue_details)

    # Breakdown dictionary for storage
    breakdown = {
        cat: {
            "raw_score": res.raw_score,
            "weighted_score": res.weighted_score,
            "coverage_pct": res.coverage_pct,
            "passed": res.checks_passed,
            "failed": res.checks_failed,
            "missing": res.checks_missing,
        }
        for cat, res in quality_res.category_scores.items()
    }
    breakdown["valuation"] = {
        "score": val_res.valuation_score,
        "call": val_res.valuation_call,
        "pe": val_res.pe_multiple,
        "reasoning": val_res.reasoning,
    }

    # 4. Save to repository
    record = repo.save_company_score(
        company_id=company.id,
        research_plan_id=plan.id,
        company_quality_score=quality_res.company_quality_score,
        ipo_valuation_score=val_res.valuation_score,
        overall_score=quality_res.company_quality_score,
        financial_perf_score=breakdown.get("financial_performance", {}).get("weighted_score"),
        business_quality_score=breakdown.get("business_quality", {}).get("weighted_score"),
        balance_sheet_score=breakdown.get("balance_sheet", {}).get("weighted_score"),
        governance_score=breakdown.get("governance", {}).get("weighted_score"),
        legal_risk_score=breakdown.get("legal_regulatory", {}).get("weighted_score"),
        industry_comp_score=breakdown.get("industry_competition", {}).get("weighted_score"),
        cash_flow_score=breakdown.get("cash_flow", {}).get("weighted_score"),
        research_coverage_pct=quality_res.research_coverage_pct,
        evidence_quality_score=quality_res.evidence_quality_score,
        score_status=quality_res.score_status,
        breakdown_json=breakdown,
        penalties_json=quality_res.penalties,
        warnings_json=quality_res.warnings,
    )

    return {
        "company_quality_score": record.company_quality_score,
        "ipo_valuation_score": record.ipo_valuation_score,
        "score_status": record.score_status,
        "research_coverage_pct": record.research_coverage_pct,
        "evidence_quality_score": record.evidence_quality_score,
        "breakdown": record.breakdown_json,
        "penalties": record.penalties_json,
        "warnings": record.warnings_json,
    }

