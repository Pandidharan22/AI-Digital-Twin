"""Citation publishing.

Builds the citation payload exactly per CITATION_SPEC.md Sec4 and publishes it to the
LiveKit data channel (topic "citations"). Fires immediately after retrieval and
BEFORE the LLM generates its reply, per ADR-005, so source cards render before
speech begins. The citation is a record of what was actually retrieved -- never
text the LLM is allowed to author.

Covers: FR-4.1, FR-4.2, FR-4.6.
"""

import json
from datetime import datetime, timezone

from livekit.agents import get_job_context

TOPIC = "citations"


async def publish(turn_id: str, query: str, retrieval_result: dict) -> None:
    """Publish one turn's citation payload to the room's data channel.

    `retrieval_result` is exactly what agent/retrieval.py's retrieve() returned
    -- this function reshapes it into the wire schema (CITATION_SPEC.md Sec4)
    and sends it, but never invents or edits a source: on `no_match` the
    `sources` list is empty, which is what makes FR-4.6 (no stale cards from a
    prior turn implying grounding that doesn't exist) hold on the frontend.

    Called from inside search_my_background before it returns to the LLM, so
    this always runs before the LLM has a chance to generate a spoken reply
    (ADR-005) -- there is no code path that generates before this is awaited.
    """
    sources = [
        {
            "id": f"cite_{i + 1}",
            "source": r["source"],
            "source_type": r["source_type"],
            "section": r["section"],
            "excerpt": r["text"],
            "score": r["score"],
            "url": r["source_url"],
        }
        for i, r in enumerate(retrieval_result["results"])
    ]

    payload = {
        "type": "citations",
        "turn_id": turn_id,
        "query": query,
        "status": retrieval_result["status"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
    }

    ctx = get_job_context()
    await ctx.room.local_participant.publish_data(json.dumps(payload), topic=TOPIC)
