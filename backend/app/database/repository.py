"""Repository abstraction layer for Companies, Checklists, Evidence, and Scoring.

Works identically on SQLite (lightweight / Termux) and PostgreSQL (server mode).
Provides robust transactional queries, error handling, and seeding routines.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session

from .schema import (
    Company,
    CompanyIdentifier,
    ResearchPlan,
    ChecklistTemplate,
    ChecklistExecution,
    EvidenceRecord,
    ChecklistEvidenceLink,
    CompanyScoreRecord,
)

log = logging.getLogger("repository")


class ResearchRepository:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # COMPANY OPERATIONS
    # -------------------------------------------------------------------------
    def create_company(
        self,
        name: str,
        legal_name: str | None = None,
        cin: str | None = None,
        industry: str | None = None,
        sector: str | None = None,
        website: str | None = None,
        description: str | None = None,
        incorporation_year: int | None = None,
    ) -> Company:
        existing = None
        if cin:
            existing = self.get_company_by_cin(cin)
        if not existing and name:
            existing = self.get_company_by_name(name)

        if existing:
            # Update fields if newly supplied
            if legal_name and not existing.legal_name:
                existing.legal_name = legal_name
            if industry and not existing.industry:
                existing.industry = industry
            if sector and not existing.sector:
                existing.sector = sector
            if website and not existing.website:
                existing.website = website
            if description and not existing.description:
                existing.description = description
            if cin and not existing.cin:
                existing.cin = cin
            self.db.commit()
            return existing

        company = Company(
            name=name.strip(),
            legal_name=legal_name.strip() if legal_name else name.strip(),
            cin=cin.strip().upper() if cin else None,
            industry=industry.strip() if industry else None,
            sector=sector.strip() if sector else None,
            website=website.strip() if website else None,
            description=description.strip() if description else None,
            incorporation_year=incorporation_year,
        )
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def get_company(self, company_id: str) -> Company | None:
        return self.db.get(Company, company_id)

    def get_company_by_cin(self, cin: str) -> Company | None:
        if not cin:
            return None
        return self.db.execute(select(Company).where(Company.cin == cin.strip().upper())).scalar_one_or_none()

    def get_company_by_name(self, name: str) -> Company | None:
        if not name:
            return None
        clean_name = name.strip().lower()
        stmt = select(Company).where(
            or_(
                func.lower(Company.name) == clean_name,
                func.lower(Company.legal_name) == clean_name
            )
        )
        return self.db.execute(stmt).scalars().first()

    def list_companies(self, limit: int = 50, offset: int = 0) -> list[Company]:
        stmt = select(Company).order_by(Company.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def add_company_identifier(
        self,
        company_id: str,
        id_type: str,
        id_value: str,
        source: str | None = None,
        is_primary: bool = False,
    ) -> CompanyIdentifier:
        clean_type = id_type.strip().lower()
        clean_val = id_value.strip()

        stmt = select(CompanyIdentifier).where(
            CompanyIdentifier.company_id == company_id,
            CompanyIdentifier.id_type == clean_type,
            CompanyIdentifier.id_value == clean_val,
        )
        existing = self.db.execute(stmt).scalar_one_or_none()
        if existing:
            return existing

        ident = CompanyIdentifier(
            company_id=company_id,
            id_type=clean_type,
            id_value=clean_val,
            source=source,
            is_primary=is_primary,
        )
        self.db.add(ident)
        self.db.commit()
        self.db.refresh(ident)
        return ident

    # -------------------------------------------------------------------------
    # CHECKLIST TEMPLATES
    # -------------------------------------------------------------------------
    def seed_checklist_template(
        self,
        template_id: str,
        category: str,
        question: str,
        description: str = "",
        retrieval_strategy: str = "hybrid",
        required_source_types: list[str] | None = None,
        calculation_rule: str = "",
        is_mandatory: bool = True,
        weight: float = 1.0,
        display_order: int = 0,
        version: str = "1.0",
    ) -> ChecklistTemplate:
        tmpl = self.db.get(ChecklistTemplate, template_id)
        if not tmpl:
            tmpl = ChecklistTemplate(
                id=template_id,
                category=category,
                question=question,
                description=description,
                retrieval_strategy=retrieval_strategy,
                required_source_types=required_source_types or [],
                calculation_rule=calculation_rule,
                is_mandatory=is_mandatory,
                weight=weight,
                display_order=display_order,
                version=version,
            )
            self.db.add(tmpl)
        else:
            tmpl.category = category
            tmpl.question = question
            tmpl.description = description
            tmpl.retrieval_strategy = retrieval_strategy
            tmpl.required_source_types = required_source_types or []
            tmpl.calculation_rule = calculation_rule
            tmpl.is_mandatory = is_mandatory
            tmpl.weight = weight
            tmpl.display_order = display_order
            tmpl.version = version
        self.db.commit()
        return tmpl

    def get_all_templates(self) -> list[ChecklistTemplate]:
        stmt = select(ChecklistTemplate).order_by(ChecklistTemplate.display_order.asc())
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # RESEARCH PLAN & EXECUTIONS
    # -------------------------------------------------------------------------
    def create_or_get_research_plan(self, company_id: str, title: str | None = None) -> ResearchPlan:
        stmt = select(ResearchPlan).where(ResearchPlan.company_id == company_id).order_by(ResearchPlan.created_at.desc())
        existing = self.db.execute(stmt).scalars().first()
        if existing and existing.status in ("pending", "in_progress"):
            return existing

        templates = self.get_all_templates()
        plan = ResearchPlan(
            company_id=company_id,
            title=title or "Automated Evidence-Based Research Plan",
            status="pending",
            total_checks=len(templates),
            completed_checks=0,
            started_at=datetime.utcnow(),
        )
        self.db.add(plan)
        self.db.flush()

        for tmpl in templates:
            execution = ChecklistExecution(
                research_plan_id=plan.id,
                template_id=tmpl.id,
                status="PENDING",
            )
            self.db.add(execution)

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_research_plan(self, plan_id: str) -> ResearchPlan | None:
        return self.db.get(ResearchPlan, plan_id)

    def get_latest_plan_for_company(self, company_id: str) -> ResearchPlan | None:
        stmt = select(ResearchPlan).where(ResearchPlan.company_id == company_id).order_by(ResearchPlan.created_at.desc())
        return self.db.execute(stmt).scalars().first()

    def update_checklist_execution(
        self,
        execution_id: str,
        status: str,
        result_value: str | None = None,
        raw_metric_value: float | None = None,
        unit: str | None = None,
        reporting_period: str | None = None,
        basis: str | None = None,
        explanation: str | None = None,
        confidence: float | None = None,
    ) -> ChecklistExecution | None:
        exec_item = self.db.get(ChecklistExecution, execution_id)
        if not exec_item:
            return None

        exec_item.status = status.upper().strip()
        exec_item.result_value = result_value
        exec_item.raw_metric_value = raw_metric_value
        exec_item.unit = unit
        exec_item.reporting_period = reporting_period
        exec_item.basis = basis
        exec_item.explanation = explanation
        exec_item.confidence = confidence
        exec_item.verified_at = datetime.utcnow()

        # Update parent plan progress
        plan = self.db.get(ResearchPlan, exec_item.research_plan_id)
        if plan:
            executions = self.db.execute(
                select(ChecklistExecution).where(ChecklistExecution.research_plan_id == plan.id)
            ).scalars().all()
            total = len(executions)
            completed = sum(1 for e in executions if e.status not in ("PENDING",))
            passed = sum(1 for e in executions if e.status == "YES")
            failed = sum(1 for e in executions if e.status == "NO")
            missing = sum(1 for e in executions if e.status == "NOT AVAILABLE")
            conflicts = sum(1 for e in executions if e.status == "CONFLICT")

            plan.total_checks = total
            plan.completed_checks = completed
            plan.passed_checks = passed
            plan.failed_checks = failed
            plan.missing_checks = missing
            plan.conflict_checks = conflicts
            plan.progress = round(completed / total, 3) if total > 0 else 0.0

            if completed == total and total > 0:
                plan.status = "completed"
                plan.completed_at = datetime.utcnow()
            elif completed > 0:
                plan.status = "in_progress"

        self.db.commit()
        self.db.refresh(exec_item)
        return exec_item

    # -------------------------------------------------------------------------
    # EVIDENCE RECORDS & CITATIONS
    # -------------------------------------------------------------------------
    def add_evidence(
        self,
        company_id: str,
        document_name: str,
        extracted_text: str,
        source_url: str | None = None,
        source_tier: str = "tier_1_official",
        source_organization: str | None = None,
        page_number: int | None = None,
        section_name: str | None = None,
        extracted_value: float | None = None,
        currency: str = "INR",
        unit: str | None = None,
        reporting_period: str | None = None,
        financial_basis: str | None = None,
        sha256_hash: str | None = None,
        is_verified: bool = True,
        verification_notes: str | None = None,
        execution_id: str | None = None,
    ) -> EvidenceRecord:
        record = EvidenceRecord(
            company_id=company_id,
            document_name=document_name,
            extracted_text=extracted_text,
            source_url=source_url,
            source_tier=source_tier,
            source_organization=source_organization,
            page_number=page_number,
            section_name=section_name,
            extracted_value=extracted_value,
            currency=currency,
            unit=unit,
            reporting_period=reporting_period,
            financial_basis=financial_basis,
            sha256_hash=sha256_hash,
            is_verified=is_verified,
            verification_notes=verification_notes,
        )
        self.db.add(record)
        self.db.flush()

        if execution_id:
            link = ChecklistEvidenceLink(execution_id=execution_id, evidence_id=record.id)
            self.db.add(link)
            # increment evidence count
            exec_item = self.db.get(ChecklistExecution, execution_id)
            if exec_item:
                exec_item.evidence_count = (exec_item.evidence_count or 0) + 1

        self.db.commit()
        self.db.refresh(record)
        return record

    def get_evidence_for_execution(self, execution_id: str) -> list[EvidenceRecord]:
        stmt = (
            select(EvidenceRecord)
            .join(ChecklistEvidenceLink, ChecklistEvidenceLink.evidence_id == EvidenceRecord.id)
            .where(ChecklistEvidenceLink.execution_id == execution_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_evidence_for_company(self, company_id: str, limit: int = 100) -> list[EvidenceRecord]:
        stmt = (
            select(EvidenceRecord)
            .where(EvidenceRecord.company_id == company_id)
            .order_by(EvidenceRecord.captured_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # COMPANY SCORING RECORDS
    # -------------------------------------------------------------------------
    def save_company_score(
        self,
        company_id: str,
        research_plan_id: str | None,
        company_quality_score: float | None,
        ipo_valuation_score: float | None,
        overall_score: float | None,
        financial_perf_score: float | None,
        business_quality_score: float | None,
        balance_sheet_score: float | None,
        governance_score: float | None,
        legal_risk_score: float | None,
        industry_comp_score: float | None,
        cash_flow_score: float | None,
        research_coverage_pct: float,
        evidence_quality_score: float,
        score_status: str,
        breakdown_json: dict,
        penalties_json: list | None = None,
        warnings_json: list | None = None,
    ) -> CompanyScoreRecord:
        record = CompanyScoreRecord(
            company_id=company_id,
            research_plan_id=research_plan_id,
            company_quality_score=company_quality_score,
            ipo_valuation_score=ipo_valuation_score,
            overall_score=overall_score,
            financial_perf_score=financial_perf_score,
            business_quality_score=business_quality_score,
            balance_sheet_score=balance_sheet_score,
            governance_score=governance_score,
            legal_risk_score=legal_risk_score,
            industry_comp_score=industry_comp_score,
            cash_flow_score=cash_flow_score,
            research_coverage_pct=research_coverage_pct,
            evidence_quality_score=evidence_quality_score,
            score_status=score_status,
            breakdown_json=breakdown_json,
            penalties_json=penalties_json or [],
            warnings_json=warnings_json or [],
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest_score_for_company(self, company_id: str) -> CompanyScoreRecord | None:
        stmt = (
            select(CompanyScoreRecord)
            .where(CompanyScoreRecord.company_id == company_id)
            .order_by(CompanyScoreRecord.calculated_at.desc())
        )
        return self.db.execute(stmt).scalars().first()

