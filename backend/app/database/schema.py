"""Extended Database Schema for Evidence-Based Indian IPO Research Platform.

Extends the core schema with normalized models for:
- Companies & Legal Identifiers (CIN, NSE/BSE tickers, ISIN)
- Multi-Source Research Plans
- 26+ Point Research Checklist & Execution Tracking
- Evidence Records (with exact page, hash, URL, reporting period, unit)
- Dual Rule-Based Scores (Company Quality Score & IPO Valuation Score)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Company(Base):
    """Primary company entity under investigation."""
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(512), index=True)
    cin: Mapped[str | None] = mapped_column(String(21), unique=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(128), index=True)
    sector: Mapped[str | None] = mapped_column(String(128), index=True)
    website: Mapped[str | None] = mapped_column(String(512))
    incorporation_year: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, draft, archived
    is_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    identifiers: Mapped[list["CompanyIdentifier"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    research_plans: Mapped[list["ResearchPlan"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    scores: Mapped[list["CompanyScoreRecord"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class CompanyIdentifier(Base):
    """Alternative names, stock tickers, MCA registrations, or external IDs."""
    __tablename__ = "company_identifiers"
    __table_args__ = (UniqueConstraint("company_id", "id_type", "id_value"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    id_type: Mapped[str] = mapped_column(String(32), index=True)  # cin, nse_symbol, bse_code, isin, cg_id, alias
    id_value: Mapped[str] = mapped_column(String(128), index=True)
    source: Mapped[str | None] = mapped_column(String(64))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship(back_populates="identifiers")


class ResearchPlan(Base):
    """Company-specific research plan driving the automated checklist."""
    __tablename__ = "research_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(256), default="Comprehensive IPO & Company Intelligence Plan")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)  # pending, in_progress, completed, failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    total_checks: Mapped[int] = mapped_column(Integer, default=0)
    completed_checks: Mapped[int] = mapped_column(Integer, default=0)
    passed_checks: Mapped[int] = mapped_column(Integer, default=0)
    failed_checks: Mapped[int] = mapped_column(Integer, default=0)
    missing_checks: Mapped[int] = mapped_column(Integer, default=0)
    conflict_checks: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship(back_populates="research_plans")
    executions: Mapped[list["ChecklistExecution"]] = relationship(back_populates="research_plan", cascade="all, delete-orphan")


class ChecklistTemplate(Base):
    """Master templates for research questions across categories."""
    __tablename__ = "checklist_templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "REV_GROWTH_YOY"
    category: Mapped[str] = mapped_column(String(64), index=True)   # profitability, financial_health, governance, etc.
    question: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    retrieval_strategy: Mapped[str] = mapped_column(String(32), default="hybrid")  # sql, hybrid, vector, keyword
    required_source_types: Mapped[list | None] = mapped_column(JSON)  # ["rhp", "financial_statement"]
    calculation_rule: Mapped[str | None] = mapped_column(Text)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[str] = mapped_column(String(16), default="1.0")


class ChecklistExecution(Base):
    """Execution status and verified result for one checklist item in a research plan."""
    __tablename__ = "checklist_executions"
    __table_args__ = (UniqueConstraint("research_plan_id", "template_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    research_plan_id: Mapped[str] = mapped_column(ForeignKey("research_plans.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("checklist_templates.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    # YES, NO, PARTIAL, PENDING, NOT AVAILABLE, CONFLICT, NOT APPLICABLE
    result_value: Mapped[str | None] = mapped_column(Text)
    raw_metric_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(32))
    reporting_period: Mapped[str | None] = mapped_column(String(32))  # e.g. FY2026, Q3FY26
    basis: Mapped[str | None] = mapped_column(String(32))             # Consolidated, Standalone
    explanation: Mapped[str | None] = mapped_column(Text)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float | None] = mapped_column(Float)           # 0.0 to 1.0
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    research_plan: Mapped[ResearchPlan] = relationship(back_populates="executions")
    template: Mapped[ChecklistTemplate] = relationship()
    evidence_links: Mapped[list["ChecklistEvidenceLink"]] = relationship(back_populates="execution", cascade="all, delete-orphan")


class EvidenceRecord(Base):
    """Atomic verifiable proof supporting an extracted fact or checklist answer."""
    __tablename__ = "evidence_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(String(36), index=True)
    document_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_tier: Mapped[str] = mapped_column(String(32), default="tier_1_official")  # tier_1_official, tier_2_institutional, tier_3_news
    source_organization: Mapped[str | None] = mapped_column(String(128))  # SEBI, NSE, BSE, MCA, CRISIL, ICRA
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_name: Mapped[str | None] = mapped_column(String(256))
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_value: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(16), default="INR")
    unit: Mapped[str | None] = mapped_column(String(32))  # crore, lakh, %, ratio
    reporting_period: Mapped[str | None] = mapped_column(String(32))
    financial_basis: Mapped[str | None] = mapped_column(String(32))  # Consolidated, Standalone
    sha256_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_notes: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship(back_populates="evidence_records")
    checklist_links: Mapped[list["ChecklistEvidenceLink"]] = relationship(back_populates="evidence", cascade="all, delete-orphan")


class ChecklistEvidenceLink(Base):
    """Many-to-Many relation connecting checklist executions to atomic evidence items."""
    __tablename__ = "checklist_evidence_links"
    __table_args__ = (UniqueConstraint("execution_id", "evidence_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    execution_id: Mapped[str] = mapped_column(ForeignKey("checklist_executions.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_records.id", ondelete="CASCADE"), index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)

    execution: Mapped[ChecklistExecution] = relationship(back_populates="evidence_links")
    evidence: Mapped[EvidenceRecord] = relationship(back_populates="checklist_links")


class CompanyScoreRecord(Base):
    """Rule-based, version-controlled company & IPO valuation scoring results."""
    __tablename__ = "company_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    research_plan_id: Mapped[str | None] = mapped_column(String(36), index=True)
    scoring_version: Mapped[str] = mapped_column(String(16), default="2.0")

    # Scores
    company_quality_score: Mapped[float | None] = mapped_column(Float)  # 0 to 100
    ipo_valuation_score: Mapped[float | None] = mapped_column(Float)    # 0 to 100
    overall_score: Mapped[float | None] = mapped_column(Float)          # Combined if applicable

    # Breakdown components (Percentages/Points)
    financial_perf_score: Mapped[float | None] = mapped_column(Float)   # Weight: 25%
    business_quality_score: Mapped[float | None] = mapped_column(Float) # Weight: 20%
    balance_sheet_score: Mapped[float | None] = mapped_column(Float)    # Weight: 15%
    governance_score: Mapped[float | None] = mapped_column(Float)       # Weight: 15%
    legal_risk_score: Mapped[float | None] = mapped_column(Float)       # Weight: 10%
    industry_comp_score: Mapped[float | None] = mapped_column(Float)    # Weight: 10%
    cash_flow_score: Mapped[float | None] = mapped_column(Float)        # Weight: 5%

    # Status & Audit
    research_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)  # % of checks completed
    evidence_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    score_status: Mapped[str] = mapped_column(String(32), default="INSUFFICIENT_EVIDENCE")
    # FINAL, PROVISIONAL, INSUFFICIENT_EVIDENCE, NOT_SCORED
    breakdown_json: Mapped[dict] = mapped_column(JSON)
    penalties_json: Mapped[list | None] = mapped_column(JSON)
    warnings_json: Mapped[list | None] = mapped_column(JSON)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship(back_populates="scores")

