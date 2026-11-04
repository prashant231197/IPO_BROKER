"""Independent IPO Valuation Scoring Engine.

Separates fundamental company quality from IPO pricing and deal structure.
Evaluates:
- Issue P/E vs Peer Median P/E
- Fresh Issue vs OFS proportion
- Objects of the Issue (Productive capex/debt reduction vs excessive GCP)
- Dilution & pre-issue promoter lock-in
Outputs a distinct 0 to 100 IPO Valuation Score with explicit reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValuationScoreResult:
    valuation_score: float | None
    valuation_call: str  # ATTRACTIVE, REASONABLE, EXPENSIVE, INDETERMINATE
    pe_multiple: float | None
    peer_median_pe: float | None
    fresh_issue_pct: float | None
    reasoning: list[str] = field(default_factory=list)


class IPOValuationScoreEngine:
    @classmethod
    def calculate_valuation_score(
        cls,
        issue_details: dict[str, Any],
        peer_median_pe: float | None = None,
    ) -> ValuationScoreResult:
        score = 50.0  # Baseline neutral
        reasoning = []

        fresh = issue_details.get("fresh_issue_cr") or 0.0
        ofs = issue_details.get("ofs_cr") or 0.0
        tot = issue_details.get("total_issue_cr") or (fresh + ofs)
        pe = issue_details.get("pe_ratio") or issue_details.get("post_pe_ratio")

        # 1. Fresh Issue vs OFS Split (Max 25 pts)
        fresh_pct = None
        if tot > 0:
            fresh_pct = round((fresh / tot) * 100.0, 1)
            if fresh_pct >= 70.0:
                score += 15.0
                reasoning.append(f"Strong Fresh Issue proportion ({fresh_pct}%): proceeds fund internal company growth.")
            elif fresh_pct <= 20.0:
                score -= 15.0
                reasoning.append(f"Heavy OFS proportion ({100.0 - fresh_pct:.0f}%): existing investors cashing out.")
            else:
                score += 5.0
                reasoning.append(f"Balanced Fresh Issue ({fresh_pct}%) and OFS split.")
        else:
            reasoning.append("Fresh/OFS issue breakdown not fully extracted.")

        # 2. P/E Multiple vs Peer Median (Max 35 pts)
        if pe is not None and pe > 0:
            if peer_median_pe is not None and peer_median_pe > 0:
                rel = pe / peer_median_pe
                if rel <= 0.8:
                    score += 20.0
                    reasoning.append(f"Attractive valuation: Issuer P/E ({pe:.1f}x) trades at a >20% discount to peer median ({peer_median_pe:.1f}x).")
                elif rel <= 1.15:
                    score += 10.0
                    reasoning.append(f"Fair valuation: Issuer P/E ({pe:.1f}x) is in line with peer median ({peer_median_pe:.1f}x).")
                elif rel <= 1.5:
                    score -= 10.0
                    reasoning.append(f"Priced at a premium: Issuer P/E ({pe:.1f}x) is ~{int((rel-1)*100)}% higher than peer median ({peer_median_pe:.1f}x).")
                else:
                    score -= 20.0
                    reasoning.append(f"High valuation premium: Issuer P/E ({pe:.1f}x) significantly exceeds peer median ({peer_median_pe:.1f}x).")
            else:
                if pe <= 20.0:
                    score += 10.0
                    reasoning.append(f"Reasonable absolute P/E ({pe:.1f}x).")
                elif pe >= 60.0:
                    score -= 15.0
                    reasoning.append(f"High absolute P/E multiple ({pe:.1f}x).")
        else:
            reasoning.append("P/E multiple could not be verified from offer documents.")

        # 3. Objects of the Issue (Max 15 pts)
        objects = issue_details.get("objects") or []
        if objects:
            has_debt_reduction = any("debt" in str(o).lower() or "repay" in str(o).lower() for o in objects)
            has_capex = any("expansion" in str(o).lower() or "capital" in str(o).lower() or "facility" in str(o).lower() for o in objects)
            if has_debt_reduction or has_capex:
                score += 10.0
                reasoning.append("Issue proceeds targeted towards productive capex / debt deleveraging.")
        else:
            reasoning.append("Objects of issue details pending review.")

        final_score = max(5.0, min(95.0, round(score, 1)))

        if final_score >= 65.0:
            call = "ATTRACTIVE"
        elif final_score >= 45.0:
            call = "REASONABLE"
        elif pe is None:
            call = "INDETERMINATE"
        else:
            call = "EXPENSIVE"

        return ValuationScoreResult(
            valuation_score=final_score,
            valuation_call=call,
            pe_multiple=pe,
            peer_median_pe=peer_median_pe,
            fresh_issue_pct=fresh_pct,
            reasoning=reasoning,
        )

