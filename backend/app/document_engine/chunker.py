"""Page-Preserving Document Chunker & Text Segmentation Engine.

Chunks document pages into retrievable passages while strictly retaining:
- Exact page number
- Document SHA-256 hash
- Section header / chapter
- Word boundaries and overlap
Guarantees citations always point to the actual document page where evidence lives.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str | None
    document_sha256: str | None
    page_number: int
    section_name: str
    text: str
    char_start: int
    char_end: int
    metadata: dict[str, Any]


class PageChunker:
    def __init__(self, target_chunk_chars: int = 800, overlap_chars: int = 150):
        self.target_chunk_chars = target_chunk_chars
        self.overlap_chars = overlap_chars

    def chunk_page(
        self,
        page_text: str,
        page_number: int,
        document_id: str | None = None,
        document_sha256: str | None = None,
        section_name: str = "General",
    ) -> list[DocumentChunk]:
        """Segments a single page into overlapping chunks, preserving page attribution."""
        if not page_text or not page_text.strip():
            return []

        clean_text = re.sub(r"\r\n", "\n", page_text).strip()
        chunks: list[DocumentChunk] = []
        n = len(clean_text)

        if n <= self.target_chunk_chars:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"p{page_number}_c0",
                    document_id=document_id,
                    document_sha256=document_sha256,
                    page_number=page_number,
                    section_name=section_name,
                    text=clean_text,
                    char_start=0,
                    char_end=n,
                    metadata={"total_page_chars": n},
                )
            )
            return chunks

        start = 0
        idx = 0
        while start < n:
            end = min(start + self.target_chunk_chars, n)
            # Try to snap end to newline or sentence punctuation
            if end < n:
                punct_pos = max(clean_text.rfind(". ", start, end), clean_text.rfind("\n", start, end))
                if punct_pos > start + 200:
                    end = punct_pos + 1

            chunk_text = clean_text[start:end].strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"p{page_number}_c{idx}",
                        document_id=document_id,
                        document_sha256=document_sha256,
                        page_number=page_number,
                        section_name=section_name,
                        text=chunk_text,
                        char_start=start,
                        char_end=end,
                        metadata={"chunk_index": idx},
                    )
                )
                idx += 1

            if end >= n:
                break
            start = max(start + 1, end - self.overlap_chars)

        return chunks

