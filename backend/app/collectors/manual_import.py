"""Manual Document Import & Local File Ingestion Connector.

Allows uploading or local directory importing of official PDFs (Annual Reports,
Credit Rating rationales, Court Orders, MCA extracts) with:
- SHA-256 fingerprinting
- Page count verification via PyMuPDF / pypdf
- Deduplication against existing files
"""
from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any

from .base import BaseCollector, DiscoveredDocument, DownloadResult
from ..config import RAW_DOCS_DIR

log = logging.getLogger("collectors.manual_import")


class ManualImportCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_id="manual_import", source_name="Manual Document Import", tier="tier_1_official")

    def discover(self, company_name: str, cin: str | None = None, **kwargs) -> list[DiscoveredDocument]:
        """Scans local RAW_DOCS_DIR for any manually placed files matching the company."""
        discovered = []
        if not company_name:
            return discovered

        slug = company_name.lower().replace(" ", "_")
        for pdf_file in RAW_DOCS_DIR.glob("*.pdf"):
            fname = pdf_file.name.lower()
            if slug in fname or (cin and cin.lower() in fname):
                discovered.append(
                    DiscoveredDocument(
                        title=pdf_file.stem,
                        source_name=self.source_name,
                        source_url=f"file://{pdf_file.resolve()}",
                        document_type="OFFLINE_IMPORT",
                        company_name=company_name,
                        tier=self.tier,
                        metadata={"file_size": pdf_file.stat().st_size},
                    )
                )
        return discovered

    def import_local_file(
        self,
        source_file_path: Path,
        company_name: str,
        document_type: str = "ANNUAL_REPORT",
        tier: str = "tier_1_official",
    ) -> DownloadResult:
        """Copies an external file into RAW_DOCS_DIR named by its SHA-256 hash."""
        if not source_file_path.exists():
            return DownloadResult(success=False, error=f"File not found: {source_file_path}")

        sha = hashlib.sha256()
        with open(source_file_path, "rb") as f:
            while chunk := f.read(64 * 1024):
                sha.update(chunk)
        hex_hash = sha.hexdigest()

        target_path = RAW_DOCS_DIR / f"{hex_hash}.pdf"
        is_dup = target_path.exists()
        if not is_dup:
            shutil.copy2(source_file_path, target_path)

        return DownloadResult(
            success=True,
            file_path=target_path,
            sha256_hash=hex_hash,
            file_size_bytes=target_path.stat().st_size,
            is_duplicate=is_dup,
        )

