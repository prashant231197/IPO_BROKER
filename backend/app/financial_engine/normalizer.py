"""Financial Unit & Period Normalizer for Indian Accounting Statements.

Enforces strict rules:
1. Never combine standalone and consolidated figures.
2. Standardize all absolute financial metrics to INR Crore (₹ Cr).
3. Distinguish annual (FY), quarterly (Q), half-yearly (H1), and 9-month (9M) periods.
4. Correctly parse Indian number conventions (Lakhs, Crores, parenthesized negatives).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Multipliers to convert to ₹ Crore
UNIT_MULTIPLIERS = {
    "crore": 1.0,
    "crores": 1.0,
    "cr": 1.0,
    "in_crores": 1.0,
    "lakh": 0.01,
    "lakhs": 0.01,
    "lac": 0.01,
    "lacs": 0.01,
    "in_lakhs": 0.01,
    "thousand": 0.0001,
    "thousands": 0.0001,
    "k": 0.0001,
    "in_thousands": 0.0001,
    "million": 0.1,
    "millions": 0.1,
    "mn": 0.1,
    "in_millions": 0.1,
    "billion": 100.0,
    "billions": 100.0,
    "bn": 100.0,
    "in_billions": 100.0,
    "rupee": 0.0000001,
    "rupees": 0.0000001,
    "inr": 0.0000001,
    "rs": 0.0000001,
}

YEAR_REGEX = re.compile(r"\b(20\d{2})\b")
FY_SHORT_REGEX = re.compile(r"\bFY\s*(\d{2,4})\b", re.I)


@dataclass
class NormalizedMetric:
    metric_name: str
    raw_value_str: str
    normalized_value: float | None
    standard_unit: str  # crore, percentage, ratio, count
    source_unit: str
    reporting_period: str
    basis: str  # Consolidated, Standalone
    is_audited: bool = True


class FinancialNormalizer:
    @staticmethod
    def parse_number(val_str: str | None) -> float | None:
        """Parses Indian numbers with commas, currency symbols, and parenthesized negatives `(123.4)`."""
        if val_str is None:
            return None
        s = str(val_str).strip()
        if not s or s in ("-", "--", "NA", "N.A.", "nil", "Nil", "NIL"):
            return None

        # Check negative in parentheses: (123.45)
        is_neg = False
        if s.startswith("(") and s.endswith(")"):
            is_neg = True
            s = s[1:-1].strip()
        elif s.startswith("-"):
            is_neg = True
            s = s[1:].strip()

        # Remove currency symbols, units, commas, and spaces
        cleaned = re.sub(r"[₹$,\s]|Rs\.?|INR|\b(cr|crore|crores|lakh|lakhs|mn|bn)\b", "", s, flags=re.I)
        try:
            val = float(cleaned)
            return -val if is_neg else val
        except ValueError:
            return None

    @staticmethod
    def detect_unit(header_or_text: str) -> str:
        """Detects financial reporting unit from table header or page text."""
        lower = header_or_text.lower()
        if "crore" in lower or "cr." in lower or "(in cr" in lower:
            return "crore"
        if "lakh" in lower or "lac" in lower or "(in lakh" in lower:
            return "lakh"
        if "million" in lower or "mn." in lower:
            return "million"
        if "billion" in lower or "bn." in lower:
            return "billion"
        if "thousand" in lower or "('000)" in lower or "(in '000" in lower:
            return "thousand"
        if "percentage" in lower or "%" in lower:
            return "percentage"
        return "crore"  # Default in Indian mainboard prospectuses

    @classmethod
    def normalize_amount(cls, raw_val: str | float | None, unit: str = "crore") -> float | None:
        """Converts raw amount in any currency scale into standard ₹ Crore."""
        if isinstance(raw_val, (int, float)):
            val = float(raw_val)
        else:
            val = cls.parse_number(str(raw_val))
        if val is None:
            return None

        multiplier = UNIT_MULTIPLIERS.get(unit.lower().strip(), 1.0)
        return round(val * multiplier, 3)

    @staticmethod
    def normalize_period(period_str: str) -> str:
        """Normalizes period strings (e.g. '31-Mar-2026', 'FY 26', 'Fiscal 2025') into standard 'FY2026'."""
        if not period_str:
            return "UNKNOWN"
        p = period_str.strip()

        # Check FY short
        m_fy = FY_SHORT_REGEX.search(p)
        if m_fy:
            yr = m_fy.group(1)
            full_yr = f"20{yr}" if len(yr) == 2 else yr
            if "9m" in p.lower():
                return f"9MFY{full_yr}"
            if "h1" in p.lower():
                return f"H1FY{full_yr}"
            if "q1" in p.lower():
                return f"Q1FY{full_yr}"
            if "q2" in p.lower():
                return f"Q2FY{full_yr}"
            if "q3" in p.lower():
                return f"Q3FY{full_yr}"
            if "q4" in p.lower():
                return f"Q4FY{full_yr}"
            return f"FY{full_yr}"

        # Check full year in date string (e.g. March 31, 2025)
        m_yr = YEAR_REGEX.search(p)
        if m_yr:
            yr = m_yr.group(1)
            # If month is June/Sep/Dec, handle interim period
            p_low = p.lower()
            if "dec" in p_low or "nine months" in p_low:
                return f"9MFY{int(yr)+1}"
            if "sep" in p_low or "half year" in p_low:
                return f"H1FY{int(yr)+1}"
            return f"FY{yr}"

        return p.upper()

    @staticmethod
    def detect_basis(text: str) -> str:
        """Distinguishes Standalone from Consolidated financial basis."""
        lower = text.lower()
        if "consolidated" in lower:
            return "Consolidated"
        if "standalone" in lower or "separate financial" in lower:
            return "Standalone"
        return "Consolidated"  # Default in RHP headline financials
