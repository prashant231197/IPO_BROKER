"""Entity Resolver & Company Legal Identity Resolution Engine.

Resolves corporate identity, normalizes company names, verifies Indian CINs,
distinguishes subsidiaries from parent/holding companies, and manages aliases.
Ensures financial information from different legal entities is never mixed.
"""
from __future__ import annotations

import re
from typing import Any

# Indian MCA Corporate Identity Number (CIN) format:
# 1 char (L/U) + 5 digits (Industry code) + 2 chars (State) + 4 digits (Year) + 3 chars (PLC/PTC) + 6 digits (Reg number)
CIN_REGEX = re.compile(r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$")

STOP_TERMS = {
    "limited", "ltd", "private", "pvt", "corp", "corporation", "inc", "incorporated",
    "co", "company", "india", "the", "and", "&", "services", "solutions", "technologies"
}

SUBSIDIARY_INDICATORS = [
    "subsidiary", "wholly owned subsidiary", "step-down", "holding company", "parent",
    "joint venture", "associate company", "group company", "affiliate"
]


class EntityResolver:
    @staticmethod
    def normalize_name(name: str) -> str:
        """Standardizes company names for deduplication and fuzzy comparison."""
        if not name:
            return ""
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", name.lower())
        tokens = [t for t in cleaned.split() if t and t not in STOP_TERMS]
        return " ".join(tokens)

    @staticmethod
    def is_valid_cin(cin: str) -> bool:
        """Validates Indian MCA CIN structure."""
        if not cin:
            return False
        clean = cin.strip().upper()
        return bool(CIN_REGEX.match(clean))

    @staticmethod
    def parse_cin_details(cin: str) -> dict[str, Any]:
        """Extracts listing status, state, year of incorporation, and type from a valid CIN."""
        clean = cin.strip().upper()
        if not EntityResolver.is_valid_cin(clean):
            return {"valid": False}
        return {
            "valid": True,
            "is_listed": clean[0] == "L",
            "industry_code": clean[1:6],
            "state_code": clean[6:8],
            "incorporation_year": int(clean[8:12]),
            "company_type": clean[12:15],  # PLC (Public Ltd) or PTC (Private Ltd)
            "registration_number": clean[15:],
        }

    @staticmethod
    def disambiguate_relation(parent_name: str, candidate_name: str, context_text: str = "") -> dict[str, Any]:
        """Determines whether candidate_name is the primary issuer, a subsidiary, or a holding company."""
        parent_norm = EntityResolver.normalize_name(parent_name)
        candidate_norm = EntityResolver.normalize_name(candidate_name)

        if parent_norm == candidate_norm:
            return {"relation": "identical", "confidence": 1.0, "is_same_entity": True}

        lower_ctx = context_text.lower()
        has_sub_indicator = any(ind in lower_ctx for ind in SUBSIDIARY_INDICATORS)
        cand_tokens = [t for t in candidate_norm.split() if len(t) > 2]
        parent_tokens = [t for t in parent_norm.split() if len(t) > 2]

        if has_sub_indicator and (any(t in lower_ctx for t in cand_tokens) or any(t in lower_ctx for t in parent_tokens)):
            matched_ind = next(ind for ind in SUBSIDIARY_INDICATORS if ind in lower_ctx)
            return {
                "relation": "related_party_or_subsidiary",
                "relationship_type": matched_ind,
                "confidence": 0.85,
                "is_same_entity": False,
            }

        # Check token containment
        parent_set = set(parent_norm.split())
        cand_set = set(candidate_norm.split())
        if parent_set and cand_set:
            overlap = len(parent_set.intersection(cand_set)) / max(len(parent_set), len(cand_set))
            if overlap >= 0.7:
                return {"relation": "likely_alias", "confidence": overlap, "is_same_entity": True}

        return {"relation": "distinct_entity", "confidence": 0.9, "is_same_entity": False}

    @classmethod
    def resolve_target(cls, query: str, registered_companies: list[dict[str, Any]]) -> dict[str, Any]:
        """Matches a search query (Name, CIN, Ticker) to registered entities with high confidence."""
        clean_q = query.strip()
        q_norm = cls.normalize_name(clean_q)

        # 1. Check exact CIN match
        if cls.is_valid_cin(clean_q):
            for comp in registered_companies:
                if (comp.get("cin") or "").upper() == clean_q.upper():
                    return {"matched": True, "company": comp, "match_type": "exact_cin", "confidence": 1.0}

        # 2. Check exact normalized name match
        for comp in registered_companies:
            comp_norm = cls.normalize_name(comp.get("name") or "")
            legal_norm = cls.normalize_name(comp.get("legal_name") or "")
            if q_norm and (q_norm == comp_norm or q_norm == legal_norm):
                return {"matched": True, "company": comp, "match_type": "exact_name", "confidence": 1.0}

        # 3. Check identifiers (NSE, BSE, Tickers)
        for comp in registered_companies:
            for ident in comp.get("identifiers", []):
                if ident.get("id_value", "").strip().upper() == clean_q.upper():
                    return {"matched": True, "company": comp, "match_type": "identifier", "confidence": 0.95}

        # 4. Partial / Token similarity
        best_match = None
        best_score = 0.0
        q_tokens = set(q_norm.split())

        if q_tokens:
            for comp in registered_companies:
                comp_norm = cls.normalize_name(comp.get("name") or "")
                c_tokens = set(comp_norm.split())
                if not c_tokens:
                    continue
                intersection = len(q_tokens.intersection(c_tokens))
                union = len(q_tokens.union(c_tokens))
                jaccard = intersection / union if union > 0 else 0
                if jaccard > best_score:
                    best_score = jaccard
                    best_match = comp

        if best_match and best_score >= 0.5:
            return {"matched": True, "company": best_match, "match_type": "fuzzy_name", "confidence": round(best_score, 2)}

        return {"matched": False, "query": query, "normalized": q_norm, "confidence": 0.0}
