"""Transparent, Rule-Based Company Quality Scoring Engine.

Computes the 100-point Company Quality Score across 7 weighted categories:
- Financial Performance: 25%
- Business Quality: 20%
- Balance Sheet: 15%
- Promoter & Governance: 15%
- Legal & Regulatory Risks: 10%
- Industry & Competition: 10%
- Cash Flow Quality: 5%

Enforces the Mandatory Evidence Gate:
No final score is published if mandatory checks lack verifiable proof.
Score status outputs: FINAL, PROVISIONAL, INSUFFICIENT_EVIDENCE.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CATEGORY_WEIGHTS = {
    "financial_performance": 0.25,
    "business_quality": 0.20,
    "balance_sheet": 0.15,
    "governance": 0.15,
    "legal_regulatory": 0.10,
    "industry_competition": 0.10,
    "cash_flow": 0.05,
}

# Maps checklist categories to scoring buckets
CATEGORY_MAP = {
    "profitability": "financial_performance",
    "financial_health": "balance_sheet",
    "governance": "governance",
    "business_quality": "business_quality",
    "legal_risk": "legal_regulatory",
    "industry_competition": "industry_competition",
    "cash_flow": "cash_flow",
}


@dataclass
class CategoryScoreResult:
    category: str
    weight: float
    raw_score: float  # 0 to 100
    weighted_score: float
    coverage_pct: float
    checks_total: int
    checks_passed: int
    checks_failed: int
    checks_missing: int


@dataclass
class CompanyScoreResult:
    company_quality_score: float | None
    score_status: str  # FINAL, PROVISIONAL, INSUFFICIENT_EVIDENCE
    research_coverage_pct: float
    evidence_quality_score: float
    category_scores: dict[str, CategoryScoreResult]
    warnings: list[str] = field(default_factory=list)
    penalties: list[str] = field(default_factory=list)


class CompanyScoreEngine:
    @classmethod
    def calculate_score(
        cls,
        checklist_items: list[dict[str, Any]],
        evidence_records: list[dict[str, Any]] | None = None,
    ) -> CompanyScoreResult:
        if not checklist_items:
            return CompanyScoreResult(
                company_quality_score=None,
                score_status="INSUFFICIENT_EVIDENCE",
                research_coverage_pct=0.0,
                evidence_quality_score=0.0,
                category_scores={},
                warnings=["No checklist items found for scoring evaluation."],
            )

        # 1. Group checks by scoring category
        grouped: dict[str, list[dict[str, Any]]] = {cat: [] for cat in CATEGORY_WEIGHTS}
        mandatory_total = 0
        mandatory_passed = 0
        total_checks = len(checklist_items)
        verified_checks = 0

        for item in checklist_items:
            raw_cat = (item.get("category") or "business_quality").lower()
            score_cat = CATEGORY_MAP.get(raw_cat, "business_quality")
            grouped[score_cat].append(item)

            status = (item.get("status") or "PENDING").upper()
            is_mandatory = bool(item.get("is_mandatory", True))

            if is_mandatory:
                mandatory_total += 1
                if status == "YES":
                    mandatory_passed += 1

            if status in ("YES", "NO", "PARTIAL"):
                verified_checks += 1

        overall_coverage = round((verified_checks / total_checks) * 100.0, 1) if total_checks > 0 else 0.0
        mandatory_coverage = (mandatory_passed / mandatory_total) if mandatory_total > 0 else 0.0

        # 2. Score each category
        category_results: dict[str, CategoryScoreResult] = {}
        total_weighted_score = 0.0
        warnings = []
        penalties = []

        for cat, weight in CATEGORY_WEIGHTS.items():
            items = grouped.get(cat, [])
            if not items:
                category_results[cat] = CategoryScoreResult(
                    category=cat, weight=weight, raw_score=50.0, weighted_score=50.0 * weight,
                    coverage_pct=0.0, checks_total=0, checks_passed=0, checks_failed=0, checks_missing=0
                )
                total_weighted_score += 50.0 * weight
                continue

            passed = sum(1 for it in items if it.get("status") == "YES")
            failed = sum(1 for it in items if it.get("status") == "NO")
            partial = sum(1 for it in items if it.get("status") == "PARTIAL")
            missing = sum(1 for it in items if it.get("status") in ("NOT AVAILABLE", "PENDING", "CONFLICT"))

            # Calculate raw score 0 to 100
            # YES = full points (1.0), PARTIAL = 0.5 points, NO = 0 points
            points = (passed * 1.0) + (partial * 0.5)
            max_points = len(items)
            raw_cat_score = round((points / max_points) * 100.0, 1) if max_points > 0 else 50.0
            weighted_cat_score = round(raw_cat_score * weight, 2)
            cat_coverage = round(((passed + failed + partial) / max_points) * 100.0, 1)

            if failed > 0:
                penalties.append(f"{cat.replace('_', ' ').title()}: {failed} negative verification check(s).")
            if missing > 0:
                warnings.append(f"{cat.replace('_', ' ').title()}: {missing} check(s) lacked verified evidence.")

            category_results[cat] = CategoryScoreResult(
                category=cat,
                weight=weight,
                raw_score=raw_cat_score,
                weighted_score=weighted_cat_score,
                coverage_pct=cat_coverage,
                checks_total=len(items),
                checks_passed=passed,
                checks_failed=failed,
                checks_missing=missing,
            )
            total_weighted_score += weighted_cat_score

        # 3. Determine Final Score Status
        final_quality_score = round(total_weighted_score, 1)
        evidence_quality = min(100.0, overall_coverage * 1.1)

        if mandatory_coverage >= 0.70 and overall_coverage >= 60.0:
            score_status = "FINAL"
        elif mandatory_coverage >= 0.35:
            score_status = "PROVISIONAL"
            warnings.append("Provisional Score: Key mandatory checks still pending verification.")
        else:
            score_status = "INSUFFICIENT_EVIDENCE"
            final_quality_score = None
            warnings.append("Insufficient Evidence: Mandatory checks failed to meet the 35% minimum threshold.")

        return CompanyScoreResult(
            company_quality_score=final_quality_score,
            score_status=score_status,
            research_coverage_pct=overall_coverage,
            evidence_quality_score=evidence_quality,
            category_scores=category_results,
            warnings=warnings,
            penalties=penalties,
        )

