"""Base Collector Interface and Document Download Protocol.

Defines the common connector contract for official sources (SEBI, NSE, BSE, MCA,
Rating Agencies, Company IR, Manual Import) with:
- SHA-256 duplicate detection
- Rate limiting and backoff retries
- Tier labeling (Tier 1 Official, Tier 2 Institutional, Tier 3 News)
- Safe local storage persistence
"""
from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import urllib.request
import urllib.error

from ..config import RAW_DOCS_DIR

log = logging.getLogger("collectors")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


@dataclass
class DiscoveredDocument:
    title: str
    source_name: str
    source_url: str
    document_type: str  # RHP, DRHP, ANNUAL_REPORT, RATING_REPORT, FILING, NOTICE
    published_date: str | None = None
    company_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tier: str = "tier_1_official"


@dataclass
class DownloadResult:
    success: bool
    file_path: Path | None = None
    sha256_hash: str | None = None
    file_size_bytes: int = 0
    is_duplicate: bool = False
    error: str | None = None


class BaseCollector(ABC):
    def __init__(self, source_id: str, source_name: str, tier: str = "tier_1_official"):
        self.source_id = source_id
        self.source_name = source_name
        self.tier = tier

    @abstractmethod
    def discover(self, company_name: str, cin: str | None = None, **kwargs) -> list[DiscoveredDocument]:
        """Search and discover public documents for a company."""
        pass

    def download_file(
        self,
        url: str,
        target_dir: Path | None = None,
        timeout: int = 45,
        max_retries: int = 3,
    ) -> DownloadResult:
        """Downloads document streamingly, computes SHA-256, and avoids duplicate disk writes."""
        if not url or not url.startswith("http"):
            return DownloadResult(success=False, error=f"Invalid URL: '{url}'")

        dest_dir = target_dir or RAW_DOCS_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)

        req = urllib.request.Request(url, headers={"User-Agent": UA})
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    sha = hashlib.sha256()
                    size = 0
                    temp_path = dest_dir / f"tmp_{int(time.time()*1000)}.part"
                    with open(temp_path, "wb") as out:
                        while chunk := response.read(64 * 1024):
                            size += len(chunk)
                            sha.update(chunk)
                            out.write(chunk)

                    hex_hash = sha.hexdigest()
                    final_path = dest_dir / f"{hex_hash}.pdf"

                    # Check for duplicate
                    if final_path.exists():
                        temp_path.unlink(missing_ok=True)
                        return DownloadResult(
                            success=True,
                            file_path=final_path,
                            sha256_hash=hex_hash,
                            file_size_bytes=final_path.stat().st_size,
                            is_duplicate=True,
                        )

                    temp_path.rename(final_path)
                    return DownloadResult(
                        success=True,
                        file_path=final_path,
                        sha256_hash=hex_hash,
                        file_size_bytes=size,
                        is_duplicate=False,
                    )
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
                last_error = str(exc)
                time.sleep(1.0 * attempt)

        return DownloadResult(success=False, error=f"Download failed after {max_retries} attempts: {last_error}")

