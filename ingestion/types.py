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
