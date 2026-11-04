"""SEBI Official Offer Documents Connector.

Directly queries the Securities and Exchange Board of India (SEBI) filings archive:
- Draft Red Herring Prospectuses (DRHP)
- Red Herring Prospectuses (RHP)
- Final Offer Documents & Corrigendums
"""
from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
from typing import Any

from .base import BaseCollector, DiscoveredDocument, UA

log = logging.getLogger("collectors.sebi")

SEBI_AJAX = "https://www.sebi.gov.in/sebiweb/ajax/home/getnewslistinfo.jsp"
ROW_RE = re.compile(
    r'<td>([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})</td>\s*<td><a href=[\'"]'
    r'(https://www\.sebi\.gov\.in/filings/[^\'"]+)[\'"][^>]*title=["\']([^"\']+)["\']',
    re.S,
)


class SebiCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_id="sebi_official", source_name="Securities and Exchange Board of India (SEBI)", tier="tier_1_official")

    def discover(self, company_name: str, cin: str | None = None, max_pages: int = 3, **kwargs) -> list[DiscoveredDocument]:
        discovered = []
        if not company_name:
            return discovered

        search_term = urllib.parse.quote(company_name.strip())
        seen_urls = set()

        for page in range(1, max_pages + 1):
            # Offer documents section: sid=3 (Filings), ssid=15 (Public Issues), smid=11 (Offer Documents)
            body = (
                f"nextValue={page}&next=n&search={search_term}&fromDate=&toDate=&fromYear=&toYear="
                f"&deptId=&sid=3&ssid=15&smid=11&ssidhidden=15&intmid=-1&sText=Filings"
            ).encode("utf-8")

            req = urllib.request.Request(
                SEBI_AJAX,
                data=body,
                headers={
                    "User-Agent": UA,
                    "Referer": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    html = r.read().decode("utf-8", "replace")
            except Exception as exc:
                log.warning("SEBI search page %d failed for '%s': %s", page, company_name, exc)
                break

            matches = ROW_RE.findall(html)
            if not matches:
                break

            for date_str, url, title in matches:
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title_clean = re.sub(r"\s+", " ", title).strip()
                t_lower = title_clean.lower()

                doc_type = "OFFER_DOCUMENT"
                if "red herring" in t_lower or "rhp" in t_lower:
                    doc_type = "RHP"
                elif "draft" in t_lower or "drhp" in t_lower:
                    doc_type = "DRHP"
                elif "corrigendum" in t_lower or "addendum" in t_lower:
                    doc_type = "CORRIGENDUM"
                elif "prospectus" in t_lower:
                    doc_type = "PROSPECTUS"

                discovered.append(
                    DiscoveredDocument(
                        title=title_clean,
                        source_name=self.source_name,
                        source_url=url,
                        document_type=doc_type,
                        published_date=date_str,
                        company_name=company_name,
                        tier=self.tier,
                        metadata={"page": page, "source": "sebi_ajax"},
                    )
                )

        return discovered

