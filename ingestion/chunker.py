"""Semantic-boundary chunker.

Splits documents on real structural boundaries (one role, one README section, one
topic block) -- never fixed token windows. Applies contextual prefixing (a one-line
"[Source: ... | Section: ...]" header) to the embedded text while storing the clean
version for citation display. Enforces the size floor/ceiling and strips README
boilerplate (badges, install steps, license, TOC).

Covers: FR-6.2. See DATA_INGESTION.md Sec3.
"""
