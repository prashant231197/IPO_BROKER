"""Unit Tests for Phase 3 & 4: Page Chunking, Financial Normalization, and Ratio Mathematics.
"""
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.document_engine.chunker import PageChunker
from app.financial_engine.normalizer import FinancialNormalizer
from app.financial_engine.ratios import RatioCalculator


def test_page_chunker_preserves_page_attribution():
    chunker = PageChunker(target_chunk_chars=300, overlap_chars=50)
    page_text = (
        "Reliance Jio Infocomm reported solid quarterly revenue growth. "
        "The consolidated subscriber base reached 470 million users. "
        "EBITDA margins remained resilient above 50 percent during the fiscal year. "
        "Operating cash flows were sufficient to fund 5G rollout and debt repayment."
    )
    chunks = chunker.chunk_page(
        page_text=page_text,
        page_number=42,
        document_id="doc_test_1",
        document_sha256="abc123hash",
        section_name="Management Discussion & Analysis",
    )

    assert len(chunks) >= 1
    for c in chunks:
        assert c.page_number == 42
        assert c.document_sha256 == "abc123hash"
        assert c.section_name == "Management Discussion & Analysis"
        assert len(c.text) > 0


def test_financial_normalizer_indian_numbers():
    assert FinancialNormalizer.parse_number("1,250.75") == 1250.75
    assert FinancialNormalizer.parse_number("(450.50)") == -450.50  # Parenthesized accounting negative
    assert FinancialNormalizer.parse_number("-80.20") == -80.20
    assert FinancialNormalizer.parse_number("₹ 5,000.00 Cr") == 5000.00
    assert FinancialNormalizer.parse_number("NIL") is None
    assert FinancialNormalizer.parse_number("-") is None


def test_unit_normalization_to_crores():
    # 10,000 Lakhs = 100 Crore
    assert FinancialNormalizer.normalize_amount("10,000", unit="lakh") == 100.0

    # 500 Millions = 50 Crore
    assert FinancialNormalizer.normalize_amount(500, unit="million") == 50.0

    # 2 Billions = 200 Crore
    assert FinancialNormalizer.normalize_amount(2.0, unit="billion") == 200.0

    # 75 Crores = 75 Crore
    assert FinancialNormalizer.normalize_amount(75.5, unit="crore") == 75.5


def test_period_and_basis_normalization():
    assert FinancialNormalizer.normalize_period("FY 26") == "FY2026"
    assert FinancialNormalizer.normalize_period("Fiscal 2025") == "FY2025"
    assert "9MFY2026" in FinancialNormalizer.normalize_period("Nine months ended Dec 31, 2025")

    assert FinancialNormalizer.detect_basis("Audited Consolidated Financial Statements") == "Consolidated"
    assert FinancialNormalizer.detect_basis("Standalone Balance Sheet") == "Standalone"


def test_ratio_calculator_correctness():
    # Operating Margin: EBITDA 300 Cr / Revenue 1,000 Cr = 30%
    assert RatioCalculator.operating_margin(300.0, 1000.0) == 30.0

    # Net Margin: PAT 150 Cr / Revenue 1,000 Cr = 15%
    assert RatioCalculator.net_profit_margin(150.0, 1000.0) == 15.0

    # RoE: PAT 150 Cr / Net Worth 750 Cr = 20%
    assert RatioCalculator.return_on_equity(150.0, 750.0) == 20.0

    # RoCE: EBIT 250 Cr / (Net Worth 750 Cr + Borrowings 250 Cr) = 250 / 1000 = 25%
    assert RatioCalculator.return_on_capital_employed(250.0, 750.0, 250.0) == 25.0

    # D/E: Borrowings 500 Cr / Net Worth 1,000 Cr = 0.5x
    assert RatioCalculator.debt_to_equity(500.0, 1000.0) == 0.5

    # Interest Coverage: EBIT 200 Cr / Finance Costs 50 Cr = 4.0x
    assert RatioCalculator.interest_coverage(200.0, 50.0) == 4.0

    # Current Ratio: Assets 400 Cr / Liab 200 Cr = 2.0x
    assert RatioCalculator.current_ratio(400.0, 200.0) == 2.0

    # CAGR: from 100 to 200 in 3 years = (200/100)^(1/3) - 1 ≈ 25.99%
    assert RatioCalculator.compound_annual_growth_rate(100.0, 200.0, 3) == 25.99

    # Div by zero safe handling
    assert RatioCalculator.debt_to_equity(100.0, 0.0) is None
    assert RatioCalculator.operating_margin(100.0, 0.0) is None

