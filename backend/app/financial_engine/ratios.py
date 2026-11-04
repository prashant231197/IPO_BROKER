"""Deterministic Financial Ratio & Growth Calculation Engine.

All ratios are calculated using independently reproducible financial accounting definitions.
Zero hallucination or arbitrary estimates.
"""
from __future__ import annotations

import math
from typing import Any


class RatioCalculator:
    @staticmethod
    def operating_margin(ebitda: float | None, revenue: float | None) -> float | None:
        """Operating Margin = EBITDA / Revenue from Operations (%)"""
        if ebitda is None or revenue is None or revenue <= 0:
            return None
        return round((ebitda / revenue) * 100.0, 2)

    @staticmethod
    def net_profit_margin(pat: float | None, revenue: float | None) -> float | None:
        """PAT Margin = Profit After Tax / Revenue from Operations (%)"""
        if pat is None or revenue is None or revenue <= 0:
            return None
        return round((pat / revenue) * 100.0, 2)

    @staticmethod
    def return_on_equity(pat: float | None, net_worth: float | None) -> float | None:
        """RoE / RoNW = PAT / Net Worth (%)"""
        if pat is None or net_worth is None or net_worth <= 0:
            return None
        return round((pat / net_worth) * 100.0, 2)

    @staticmethod
    def return_on_capital_employed(
        ebit: float | None,
        net_worth: float | None,
        total_borrowings: float | None = 0.0,
    ) -> float | None:
        """RoCE = EBIT / Capital Employed (Net Worth + Borrowings) (%)"""
        if ebit is None or net_worth is None:
            return None
        cap_employed = net_worth + (total_borrowings or 0.0)
        if cap_employed <= 0:
            return None
        return round((ebit / cap_employed) * 100.0, 2)

    @staticmethod
    def debt_to_equity(total_borrowings: float | None, net_worth: float | None) -> float | None:
        """D/E Ratio = Total Borrowings / Net Worth (ratio)"""
        if total_borrowings is None or net_worth is None or net_worth <= 0:
            return None
        return round(total_borrowings / net_worth, 3)

    @staticmethod
    def interest_coverage(ebit: float | None, finance_costs: float | None) -> float | None:
        """Interest Coverage = EBIT / Finance Costs (x)"""
        if ebit is None or finance_costs is None or finance_costs <= 0:
            return None
        return round(ebit / finance_costs, 2)

    @staticmethod
    def current_ratio(current_assets: float | None, current_liabilities: float | None) -> float | None:
        """Current Ratio = Current Assets / Current Liabilities (x)"""
        if current_assets is None or current_liabilities is None or current_liabilities <= 0:
            return None
        return round(current_assets / current_liabilities, 2)

    @staticmethod
    def cfo_to_pat(cfo: float | None, pat: float | None) -> float | None:
        """Cash Quality = Cash Flow from Operations / PAT (ratio)"""
        if cfo is None or pat is None or pat == 0:
            return None
        return round(cfo / pat, 2)

    @staticmethod
    def compound_annual_growth_rate(start_val: float | None, end_val: float | None, years: int) -> float | None:
        """CAGR = (End / Start) ** (1/years) - 1 (%)"""
        if start_val is None or end_val is None or years <= 0:
            return None
        if start_val <= 0 or end_val <= 0:
            return None
        try:
            rate = (math.pow(end_val / start_val, 1.0 / years) - 1.0) * 100.0
            return round(rate, 2)
        except (ValueError, ZeroDivisionError):
            return None

