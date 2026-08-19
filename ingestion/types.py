"""Shared types passed between loaders and the chunker.

A RawSection is one structural unit a loader has identified (one resume role,
one context.md topic block, one README section) -- not yet size-checked,
hashed, or embedded. That's the chunker's job. Keeping this in one place means
all three loaders and the chunker agree on the same shape.
"""

from typing import NamedTuple, Optional


class RawSection(NamedTuple):
    source: str
    source_type: str
    section: str
    text: str
    source_url: Optional[str] = None


class ChunkRecord(NamedTuple):
    """A finalized chunk: floor/ceiling-checked, hashed, ready to embed and store.

    `text` is the clean version stored and shown on citation cards. `embed_text`
    carries the contextual prefix and is only ever used to compute the
    embedding -- it never gets written to a column.
    """

    source: str
    source_type: str
    section: str
    text: str
    source_url: Optional[str]
    content_hash: str
    embed_text: str
