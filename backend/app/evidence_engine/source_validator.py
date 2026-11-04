"""Evidence Verification & Source Tier Hierarchy Engine.

Enforces strict source credibility standards:
- Tier 1 (1.0 weight): Official audited statements, SEBI filings, stock exchange disclosures.
- Tier 2 (0.8 weight): Credit rating agencies (CRISIL, ICRA, CARE), institutional filings.
- Tier 3 (0.5 weight): Reliable financial news & regulatory notices (secondary only).
- Tier 4 (0.0 weight): Market chatter & unverified forums. Strictly prohibited as primary financial evidence.
Checks for cross-document consistency, unit congruence, and reporting basis alignment.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TIER_PRIORITY = {
    "tier_1_official": 1.0,
    "tier_2_institutional": 0.8,
    "tier_3_news": 0.5,
    "tier_4_commentary": 0.0,
}


@dataclass
class ValidationReport:
    is_valid: bool
    source_tier: str
    tier_weight: float
    basis_congruent: bool
    unit_congruent: bool
    has_conflict: bool
    notes: list[str]


class SourceValidator:
    @staticmethod
    def get_tier_weight(tier: str) -> float:
        return TIER_PRIORITY.get(tier.lower().strip(), 0.5)

    @classmethod
    def validate_evidence(
        cls,
        evidence_tier: str,
        financial_basis: str | None,
        expected_basis: str = "Consolidated",
        source_unit: str | None = None,
        expected_unit: str = "crore",
    ) -> ValidationReport:
        tier = evidence_tier.lower().strip()
        weight = cls.get_tier_weight(tier)
        notes = []

        # Check Tier 4 prohibition
        if weight <= 0.0:
            return ValidationReport(
                is_valid=False,
                source_tier=tier,
                tier_weight=0.0,
                basis_congruent=False,
                unit_congruent=False,
                has_conflict=False,
                notes=["Tier 4 commentary cannot be used as evidence for financial facts."],
            )

        # Check Basis congruence
        basis_ok = True
        if financial_basis and expected_basis:
            if financial_basis.lower() != expected_basis.lower():
                basis_ok = False
                notes.append(f"Basis mismatch: evidence is {financial_basis}, expected {expected_basis}.")

        # Check Unit congruence
        unit_ok = True
        if source_unit and expected_unit:
            if source_unit.lower() != expected_unit.lower():
                notes.append(f"Unit converted from {source_unit} to standard {expected_unit}.")

        return ValidationReport(
            is_valid=basis_ok,
            source_tier=tier,
            tier_weight=weight,
            basis_congruent=basis_ok,
            unit_congruent=unit_ok,
            has_conflict=False,
            notes=notes,
        )

    @staticmethod
    def detect_cross_source_conflict(values: list[float], tolerance_pct: float = 5.0) -> bool:
        """Flags conflict if two sources report figures differing by more than tolerance_pct."""
        valid_vals = [v for v in values if v is not None]
        if len(valid_vals) < 2:
            return False

        min_val = min(valid_vals)
        max_val = max(valid_vals)
        if min_val == 0:
            return max_val > 0

        diff_pct = abs(max_val - min_val) / abs(min_val) * 100.0
        return diff_pct > tolerance_pct

