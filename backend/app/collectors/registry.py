"""Central Data Source Registry & Collector Dispatcher.

Orchestrates multi-source discovery across official repositories (SEBI, Chittorgarh,
Manual Import, Rating Agencies) with priority tier management.
"""
from __future__ import annotations

import logging
from typing import Any

from .base import BaseCollector, DiscoveredDocument
from .sebi import SebiCollector
from .chittorgarh import ChittorgarhCollector
from .manual_import import ManualImportCollector

log = logging.getLogger("collectors.registry")


class SourceRegistry:
    def __init__(self):
        self._collectors: dict[str, BaseCollector] = {
            "sebi_official": SebiCollector(),
            "chittorgarh": ChittorgarhCollector(),
            "manual_import": ManualImportCollector(),
        }

    def register(self, collector: BaseCollector) -> None:
        self._collectors[collector.source_id] = collector

    def get(self, source_id: str) -> BaseCollector | None:
        return self._collectors.get(source_id)

    def list_sources(self) -> list[dict[str, Any]]:
        return [{
            "id": c.source_id,
            "name": c.source_name,
            "tier": c.tier,
            "is_official": c.tier == "tier_1_official",
        } for c in self._collectors.values()]

    def discover_all(self, company_name: str, cin: str | None = None, **kwargs) -> list[DiscoveredDocument]:
        """Queries all registered collectors, aggregates findings, and removes duplicate URLs."""
        all_discovered: list[DiscoveredDocument] = []
        seen_urls: set[str] = set()

        for source_id, collector in self._collectors.items():
            try:
                findings = collector.discover(company_name, cin=cin, **kwargs)
                for doc in findings:
                    if doc.source_url not in seen_urls:
                        seen_urls.add(doc.source_url)
                        all_discovered.append(doc)
            except Exception as exc:
                log.warning("Collector '%s' raised an unexpected error: %s", source_id, exc)

        # Sort priority: Tier 1 official first, then RHP, then DRHP
        type_priority = {"RHP": 1, "PROSPECTUS": 2, "DRHP": 3, "CORRIGENDUM": 4}
        all_discovered.sort(
            key=lambda d: (
                0 if d.tier == "tier_1_official" else 1,
                type_priority.get(d.document_type, 10),
            )
        )
        return all_discovered


# Global singleton registry
registry = SourceRegistry()

