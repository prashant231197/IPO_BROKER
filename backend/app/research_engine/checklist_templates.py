"""Master 26-Point Research Checklist Templates for Indian IPOs.

Defines the canonical research plan structure covering:
- Profitability & Revenue Growth
- Financial Health & Balance Sheet Leverage
- Promoters & Corporate Governance
- IPO Structure & Valuation
- Business Quality, Customer Concentration & Legal Risks
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ChecklistItemDef:
    id: str
    category: str
    question: str
    description: str
    retrieval_strategy: str  # sql, hybrid, keyword, vector
    required_source_types: list[str]
    calculation_rule: str
    is_mandatory: bool
    weight: float
    display_order: int


MASTER_CHECKLIST_ITEMS: list[ChecklistItemDef] = [
    # -------------------------------------------------------------------------
    # A. PROFITABILITY & CASH GENERATION
    # -------------------------------------------------------------------------
    ChecklistItemDef(
        id="CHK_PROFIT_POS_PAT",
        category="profitability",
        question="Has the company reported positive PAT in the latest reported financial year?",
        description="Verifies audited Profit After Tax (PAT) on a consolidated basis for the most recent full year.",
        retrieval_strategy="sql",
        required_source_types=["RHP", "ANNUAL_REPORT", "FINANCIAL_STATEMENT"],
        calculation_rule="latest_pat > 0",
        is_mandatory=True,
        weight=1.5,
        display_order=1,
    ),
    ChecklistItemDef(
        id="CHK_PROFIT_3YR_PAT",
        category="profitability",
        question="Was PAT positive in each of the last 3 financial years?",
        description="Checks consistency of earnings. Multi-year profitability separates real businesses from pre-IPO dressed-up numbers.",
        retrieval_strategy="sql",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="all(pat > 0 for pat in last_3_years)",
        is_mandatory=True,
        weight=1.5,
        display_order=2,
    ),
    ChecklistItemDef(
        id="CHK_PROFIT_REV_YOY",
        category="profitability",
        question="Is revenue from operations growing year over year?",
        description="Verifies top-line expansion across the reported financial periods.",
        retrieval_strategy="sql",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="revenue_cagr > 0 or latest_revenue > prev_revenue",
        is_mandatory=True,
        weight=1.2,
        display_order=3,
    ),
    ChecklistItemDef(
        id="CHK_PROFIT_OP_MARGIN",
        category="profitability",
        question="Are operating (EBITDA) margins improving or stable?",
        description="Checks pricing power and operating leverage. EBITDA margin should ideally be >= 10%.",
        retrieval_strategy="sql",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="ebitda_margin >= 10.0 or ebitda_margin >= prev_ebitda_margin",
        is_mandatory=False,
        weight=1.0,
        display_order=4,
    ),
    ChecklistItemDef(
        id="CHK_PROFIT_POS_CFO",
        category="profitability",
        question="Is operating cash flow (CFO) positive in the latest period?",
        description="Confirms that reported earnings are backed by positive cash generated from core operations.",
        retrieval_strategy="sql",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="latest_cfo > 0",
        is_mandatory=True,
        weight=1.2,
        display_order=5,
    ),
    ChecklistItemDef(
        id="CHK_PROFIT_CFO_VS_PAT",
        category="profitability",
        question="Is profit supported by actual cash generation (CFO / PAT >= 0.7)?",
        description="Detects revenue recognition aggression. CFO / PAT ratio below 0.5 indicates weak earnings quality.",
        retrieval_strategy="sql",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="cfo / pat >= 0.7",
        is_mandatory=False,
        weight=1.0,
        display_order=6,
    ),

    # -------------------------------------------------------------------------
    # B. FINANCIAL HEALTH & BALANCE SHEET
    # -------------------------------------------------------------------------
    ChecklistItemDef(
        id="CHK_FIN_TOTAL_DEBT",
        category="financial_health",
        question="Total debt and borrowings identified and verified?",
        description="Extracts current and non-current borrowings from audited balance sheet disclosures.",
        retrieval_strategy="sql",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="total_borrowings is not None",
        is_mandatory=True,
        weight=1.0,
        display_order=7,
    ),
    ChecklistItemDef(
        id="CHK_FIN_DEBT_EQUITY",
        category="financial_health",
        question="Debt-to-equity calculated and below 1.5x?",
        description="High leverage entering an IPO transmits balance sheet risk to equity holders.",
        retrieval_strategy="sql",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="debt_to_equity <= 1.5",
        is_mandatory=True,
        weight=1.5,
        display_order=8,
    ),
    ChecklistItemDef(
        id="CHK_FIN_INT_COVER",
        category="financial_health",
        question="Interest coverage ratio calculated and above 2.5x?",
        description="Measures ability to service debt from operating profit (EBIT / Finance Cost).",
        retrieval_strategy="sql",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="interest_coverage >= 2.5",
        is_mandatory=False,
        weight=1.0,
        display_order=9,
    ),
    ChecklistItemDef(
        id="CHK_FIN_CONTINGENT_LIAB",
        category="financial_health",
        question="Contingent liabilities reviewed and quantified vs Net Worth?",
        description="Identifies off-balance-sheet tax claims, bank guarantees, and pending demands.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="contingent_liab / net_worth < 0.3",
        is_mandatory=True,
        weight=1.0,
        display_order=10,
    ),
    ChecklistItemDef(
        id="CHK_FIN_AUDITOR_QUAL",
        category="financial_health",
        question="Auditor qualifications, adverse remarks or emphasis of matter checked?",
        description="Scans the restated auditor report for modifications or going-concern doubts.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="no_auditor_qualifications",
        is_mandatory=True,
        weight=1.5,
        display_order=11,
    ),

    # -------------------------------------------------------------------------
    # C. PROMOTERS & CORPORATE GOVERNANCE
    # -------------------------------------------------------------------------
    ChecklistItemDef(
        id="CHK_GOV_PROMOTER_HOLDING",
        category="governance",
        question="Promoter shareholding pre-issue and post-issue verified?",
        description="Confirms promoter skin-in-the-game. Post-issue promoter holding should ideally remain >= 40%.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "PROSPECTUS"],
        calculation_rule="post_promoter_pct >= 40.0",
        is_mandatory=True,
        weight=1.2,
        display_order=12,
    ),
    ChecklistItemDef(
        id="CHK_GOV_PROMOTER_PLEDGE",
        category="governance",
        question="Promoter share pledge checked (zero or disclosed)?",
        description="Verifies whether any promoter shares are pledged or encumbered with lenders.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "PROSPECTUS"],
        calculation_rule="pledged_shares == 0",
        is_mandatory=True,
        weight=1.5,
        display_order=13,
    ),
    ChecklistItemDef(
        id="CHK_GOV_RPT",
        category="governance",
        question="Related-party transactions (RPTs) reviewed for conflicts?",
        description="Examines loans, guarantees, or material purchases/sales with promoter group entities.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="no_high_risk_rpt",
        is_mandatory=False,
        weight=1.0,
        display_order=14,
    ),
    ChecklistItemDef(
        id="CHK_GOV_MGMT_BACKGROUND",
        category="governance",
        question="Management and key directorial background verified?",
        description="Verifies executive tenure, qualifications, and past regulatory debars.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP"],
        calculation_rule="management_disclosed",
        is_mandatory=False,
        weight=1.0,
        display_order=15,
    ),
    ChecklistItemDef(
        id="CHK_GOV_CONCERNS",
        category="governance",
        question="Corporate governance structure and independent directors verified?",
        description="Checks audit committee, independent director ratio, and board composition.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="board_independence_ok",
        is_mandatory=False,
        weight=0.8,
        display_order=16,
    ),

    # -------------------------------------------------------------------------
    # D. IPO STRUCTURE & VALUATION
    # -------------------------------------------------------------------------
    ChecklistItemDef(
        id="CHK_IPO_FRESH_VS_OFS",
        category="ipo_valuation",
        question="Fresh issue vs Offer for Sale (OFS) split verified?",
        description="Distinguishes growth capital entering the company vs existing investors selling out.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "PROSPECTUS"],
        calculation_rule="fresh_issue_cr > 0",
        is_mandatory=True,
        weight=1.2,
        display_order=17,
    ),
    ChecklistItemDef(
        id="CHK_IPO_OBJECTS",
        category="ipo_valuation",
        question="Objects of the issue analyzed and verified?",
        description="Breakdown of IPO proceeds: organic expansion, debt reduction, acquisitions, or GCP.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "PROSPECTUS"],
        calculation_rule="objects_specified and gcp_pct <= 25.0",
        is_mandatory=True,
        weight=1.0,
        display_order=18,
    ),
    ChecklistItemDef(
        id="CHK_IPO_PE_RATIO",
        category="ipo_valuation",
        question="Post-issue EPS and P/E ratio calculated at price band?",
        description="Calculates price-to-earnings multiple at the upper price band based on restated EPS.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "PROSPECTUS"],
        calculation_rule="pe_ratio is not None and pe_ratio > 0",
        is_mandatory=True,
        weight=1.5,
        display_order=19,
    ),
    ChecklistItemDef(
        id="CHK_IPO_PEER_VALUATION",
        category="ipo_valuation",
        question="Peer valuation compared against listed industry peers?",
        description="Compares issuer P/E, RoNW, and EV/EBITDA against peer comparison table in Basis for Offer Price.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "PROSPECTUS"],
        calculation_rule="issuer_pe <= peer_median_pe * 1.15",
        is_mandatory=False,
        weight=1.2,
        display_order=20,
    ),
    ChecklistItemDef(
        id="CHK_IPO_DILUTION",
        category="ipo_valuation",
        question="Equity dilution after IPO calculated?",
        description="Percentage of post-issue share capital offered to the public.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "PROSPECTUS"],
        calculation_rule="dilution_pct > 0",
        is_mandatory=False,
        weight=0.8,
        display_order=21,
    ),

    # -------------------------------------------------------------------------
    # E. BUSINESS QUALITY & LEGAL RISKS
    # -------------------------------------------------------------------------
    ChecklistItemDef(
        id="CHK_RISK_BIZ_MODEL",
        category="business_quality",
        question="Core business model and revenue drivers understood?",
        description="Clear breakdown of product/service segments, revenue concentration, and key geographies.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "ANNUAL_REPORT"],
        calculation_rule="business_description_verified",
        is_mandatory=True,
        weight=1.2,
        display_order=22,
    ),
    ChecklistItemDef(
        id="CHK_RISK_CUSTOMER_CONC",
        category="business_quality",
        question="Customer concentration checked (<50% revenue from top 10)?",
        description="Evaluates revenue dependency on anchor clients or specific key accounts.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP"],
        calculation_rule="top_10_customer_pct < 50.0",
        is_mandatory=False,
        weight=1.0,
        display_order=23,
    ),
    ChecklistItemDef(
        id="CHK_RISK_COMPETITION",
        category="business_quality",
        question="Industry competitive dynamics and market share analyzed?",
        description="Examines barriers to entry, pricing discipline, and competitive intensity in the sector.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "RATING_REPORT"],
        calculation_rule="industry_overview_verified",
        is_mandatory=False,
        weight=0.8,
        display_order=24,
    ),
    ChecklistItemDef(
        id="CHK_RISK_LITIGATION",
        category="legal_risk",
        question="Material litigation disclosures against company, promoters & directors reviewed?",
        description="Assesses criminal proceedings, tax disputes, and regulatory penalties under Outstanding Litigation.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "PROSPECTUS"],
        calculation_rule="no_critical_criminal_proceedings",
        is_mandatory=True,
        weight=1.5,
        display_order=25,
    ),
    ChecklistItemDef(
        id="CHK_RISK_REGULATORY",
        category="legal_risk",
        question="Regulatory approvals, licenses and sector compliance risks reviewed?",
        description="Identifies material regulatory notices, license expirations, or environmental liabilities.",
        retrieval_strategy="hybrid",
        required_source_types=["RHP", "PROSPECTUS"],
        calculation_rule="regulatory_risk_evaluated",
        is_mandatory=True,
        weight=1.0,
        display_order=26,
    ),
]


def seed_master_templates(repo) -> None:
    """Seeds the master 26 checklist items into the database."""
    for item in MASTER_CHECKLIST_ITEMS:
        repo.seed_checklist_template(
            template_id=item.id,
            category=item.category,
            question=item.question,
            description=item.description,
            retrieval_strategy=item.retrieval_strategy,
            required_source_types=item.required_source_types,
            calculation_rule=item.calculation_rule,
            is_mandatory=item.is_mandatory,
            weight=item.weight,
            display_order=item.display_order,
        )

