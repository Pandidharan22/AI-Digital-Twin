"""Retrieval and grounding gate.

Embeds the incoming query with the same local model used at ingestion time, runs
pgvector cosine-similarity search via Supabase's match_chunks function, and applies
RETRIEVAL_THRESHOLD to decide match vs no_match. Returns the exact contract shape
defined in CITATION_SPEC.md Sec3, including the no_match instruction field.

Covers: FR-3.2, FR-3.3. Load-bearing anti-hallucination layer (ADR-004, L1 in
CITATION_SPEC.md Sec2).
"""

import asyncio
from functools import lru_cache
from typing import TypedDict

from supabase import Client, create_client

from . import config
from ingestion.embedder import embed_query

NO_MATCH_INSTRUCTION = (
    "No documented information found. Tell the user you do not have this "
    "documented. Do not answer from general knowledge."
)


class RetrievedChunk(TypedDict):
    source: str
    source_type: str
    section: str
    text: str
    score: float
    source_url: str | None


@lru_cache(maxsize=1)
def _client() -> Client:
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def _match_sync(query: str) -> list[RetrievedChunk]:
    """Blocking: local CPU embedding + a synchronous supabase-py HTTP call.

    supabase-py has no async client, and sentence-transformers' .encode() is
    CPU-bound -- both would stall the worker's event loop (and every other
    room it's servicing) if called directly from an async function. retrieve()
    below pushes this whole function to a thread instead.
    """
    embedding = embed_query(query)
    resp = (
        _client()
        .rpc(
            "match_chunks",
            {
                "query_embedding": embedding,
                "query_text": query,
                "match_threshold": config.RETRIEVAL_THRESHOLD,
                "match_count": config.RETRIEVAL_TOP_K,
            },
        )
        .execute()
    )
    return [
        {
            "source": r["source"],
            "source_type": r["source_type"],
            "section": r["section"],
            "text": r["text"],
            "score": r["similarity"],
            "source_url": r["source_url"],
        }
        for r in resp.data
    ]


async def retrieve(query: str) -> dict:
    """Search the corpus for `query` and return the CITATION_SPEC.md Sec3 contract.

    `status: "match"` with up to RETRIEVAL_TOP_K chunks that cleared
    RETRIEVAL_THRESHOLD, or `status: "no_match"` with an empty result set and
    an explicit refusal instruction -- deliberately placed in the returned
    data (not only the system prompt) so the refusal directive sits right next
    to the decision point (ADR-004).
    """
    results = await asyncio.to_thread(_match_sync, query)
    if not results:
        return {"status": "no_match", "results": [], "instruction": NO_MATCH_INSTRUCTION}
    return {"status": "match", "results": results}
