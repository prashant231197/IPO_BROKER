"""Chittorgarh IPO Intelligence Connector.

Discovers Indian IPO issue metadata, prospectus URLs (RHP/DRHP), and restated financials.
Reads from local cached records (data/cg_records.json & data/cg_issue.csv) first for fast,
offline Termux capability, with optional live fetching fallback.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from .base import BaseCollector, DiscoveredDocument
from ..config import DATA_DIR
from ..discovery.entity_resolver import EntityResolver

log = logging.getLogger("collectors.chittorgarh")


class ChittorgarhCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_id="chittorgarh", source_name="Chittorgarh IPO Database", tier="tier_1_official")
        self.records_path = DATA_DIR / "cg_records.json"
        self._cached_records: dict[str, Any] | None = None

    def _get_records(self) -> dict[str, Any]:
        if self._cached_records is None:
            if self.records_path.exists():
                try:
                    self._cached_records = json.loads(self.records_path.read_text(encoding="utf-8"))
                except Exception as exc:
                    log.warning("Could not read local cg_records.json: %s", exc)
                    self._cached_records = {}
            else:
                self._cached_records = {}
        return self._cached_records

    def discover(self, company_name: str, cin: str | None = None, **kwargs) -> list[DiscoveredDocument]:
        discovered = []
        if not company_name:
            return discovered

        norm_target = EntityResolver.normalize_name(company_name)
        records = self._get_records()

        for cid, rec in records.items():
            comp_name = rec.get("company_name") or ""
            norm_comp = EntityResolver.normalize_name(comp_name)

            # Match exact or strong token overlap
            is_match = False
            if norm_target and norm_comp:
                if norm_target == norm_comp:
                    is_match = True
                else:
                    t_tokens = set(norm_target.split())
                    c_tokens = set(norm_comp.split())
                    if t_tokens and c_tokens:
                        overlap = len(t_tokens.intersection(c_tokens)) / max(len(t_tokens), len(c_tokens))
                        if overlap >= 0.7:
                            is_match = True

            if not is_match:
                continue

            # Check prospectus links
            rhp_url = rec.get("prospectus_rhp")
            drhp_url = rec.get("prospectus_drhp")
            final_url = rec.get("final_prospectus")

            if rhp_url and isinstance(rhp_url, str) and rhp_url.startswith("http"):
                discovered.append(
                    DiscoveredDocument(
                        title=f"{comp_name} - Red Herring Prospectus (RHP)",
                        source_name=self.source_name,
                        source_url=rhp_url,
                        document_type="RHP",
                        published_date=rec.get("issue_open_date"),
                        company_name=comp_name,
                        tier=self.tier,
                        metadata={"cg_id": cid, "market_lot": rec.get("market_lot_size"), "pe_ratio": rec.get("pe_ratio")},
                    )
                )

            if drhp_url and isinstance(drhp_url, str) and drhp_url.startswith("http"):
                discovered.append(
                    DiscoveredDocument(
                        title=f"{comp_name} - Draft Red Herring Prospectus (DRHP)",
                        source_name=self.source_name,
                        source_url=drhp_url,
                        document_type="DRHP",
                        published_date=rec.get("issue_open_date"),
                        company_name=comp_name,
                        tier=self.tier,
                        metadata={"cg_id": cid},
                    )
                )

            if final_url and isinstance(final_url, str) and final_url.startswith("http") and final_url != rhp_url:
                discovered.append(
                    DiscoveredDocument(
                        title=f"{comp_name} - Final Prospectus",
                        source_name=self.source_name,
                        source_url=final_url,
                        document_type="PROSPECTUS",
                        published_date=rec.get("issue_close_date"),
                        company_name=comp_name,
                        tier=self.tier,
                        metadata={"cg_id": cid},
                    )
                )

        return discovered

