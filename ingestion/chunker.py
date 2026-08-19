"""Semantic-boundary chunker.

Takes loader output (RawSection: already split on real structural boundaries --
one role, one README section, one topic block) and finalizes it into
ChunkRecords: enforces the size floor/ceiling from DATA_INGESTION.md Sec3
(discard under ~40 tokens as noise, split over ~500 tokens on paragraph/sentence
boundaries while repeating the parent section label), builds the contextual-
prefix embed-text ("[Source: ... | Section: ...]" header) while keeping the
clean text for citation display, and computes content_hash for idempotent
upsert.

Boilerplate stripping (badges, install/license/TOC sections) happens in
github_loader.py at the source, since it's specific to that one loader's
input shape -- nothing left for this module to strip generically.

Covers: FR-6.2. See DATA_INGESTION.md Sec3.
"""

import hashlib
import re
from typing import List

import tiktoken

from ingestion.types import ChunkRecord, RawSection

_ENC = tiktoken.get_encoding("cl100k_base")

FLOOR_TOKENS = 40
CEILING_TOKENS = 500


def _token_count(text: str) -> int:
    return len(_ENC.encode(text))


def _content_hash(source: str, section: str, text: str) -> str:
    raw = f"{source}\x1f{section}\x1f{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _split_oversized(text: str) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(paragraphs) <= 1:
        return [text]

    parts: List[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current} {para}".strip() if current else para
        if current and _token_count(candidate) > CEILING_TOKENS:
            parts.append(current)
            current = para
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def chunk(raw_sections: List[RawSection]) -> List[ChunkRecord]:
    records: List[ChunkRecord] = []

    for raw in raw_sections:
        text = re.sub(r"[ \t]+", " ", raw.text).strip()
        if not text:
            continue

        pieces = [text] if _token_count(text) <= CEILING_TOKENS else _split_oversized(text)

        # A paragraph/sentence split can leave a trailing sliver under the
        # floor -- merge it into the previous piece instead of losing content
        # that was only ever too small because of where the split landed.
        merged: List[str] = []
        for piece in pieces:
            if merged and _token_count(piece) < FLOOR_TOKENS:
                merged[-1] = f"{merged[-1]} {piece}".strip()
            else:
                merged.append(piece)

        for piece in merged:
            if _token_count(piece) < FLOOR_TOKENS:
                continue  # headers/noise, per DATA_INGESTION.md Sec3
            records.append(
                ChunkRecord(
                    source=raw.source,
                    source_type=raw.source_type,
                    section=raw.section,
                    text=piece,
                    source_url=raw.source_url,
                    content_hash=_content_hash(raw.source, raw.section, piece),
                    embed_text=f"[Source: {raw.source} | Section: {raw.section}]\n{piece}",
                )
            )

    return records
