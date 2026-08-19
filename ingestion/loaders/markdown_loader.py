"""Local markdown loader.

Loads corpus/context.md (and any future corpus/**/*.md, excluding README.md),
splitting on `##` section boundaries per DATA_INGESTION.md Sec3 -- one topic
block per chunk. The file's top-level `#` title and any preamble before the
first `##` is meta-commentary about the file itself, not content about the
owner, so it's intentionally not yielded as a chunk.
"""

import re
from pathlib import Path
from typing import List

from ingestion.types import RawSection

SOURCE_TYPE = "context"


def load(md_path: Path) -> List[RawSection]:
    text = md_path.read_text(encoding="utf-8")
    source = md_path.name

    parts = re.split(r"^## +", text, flags=re.MULTILINE)
    results: List[RawSection] = []

    for part in parts[1:]:  # parts[0] is the preamble before the first ##
        header, _, body = part.partition("\n")
        header = header.strip()
        body = body.strip()
        if not header or not body:
            continue
        results.append(RawSection(source, SOURCE_TYPE, header, body))

    return results


def load_corpus_markdown(corpus_dir: Path) -> List[RawSection]:
    """Load every corpus/**/*.md except README.md."""
    results: List[RawSection] = []
    for md_path in sorted(corpus_dir.rglob("*.md")):
        if md_path.name.upper() == "README.MD":
            continue
        results.extend(load(md_path))
    return results
