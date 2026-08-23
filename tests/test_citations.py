"""Contract test for agent/citations.py's data-channel payload
(CITATION_SPEC.md Sec4).

Unit-level: get_job_context() is monkeypatched so this never touches a real
LiveKit room or job -- it verifies citations.publish() builds the exact wire
shape CitationsPanel.tsx depends on, from a plain dict input, in well under
a second. It does NOT verify a citation actually reaches a real frontend --
that's what TEST_PLAN.md Suite C's live voice run covers.
"""

import json
from datetime import datetime

import pytest

from agent import citations


class _FakeLocalParticipant:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish_data(self, payload: str, *, topic: str) -> None:
        self.published.append((payload, topic))


class _FakeRoom:
    def __init__(self) -> None:
        self.local_participant = _FakeLocalParticipant()


class _FakeJobContext:
    def __init__(self) -> None:
        self.room = _FakeRoom()


@pytest.fixture
def fake_ctx(monkeypatch: pytest.MonkeyPatch) -> _FakeJobContext:
    ctx = _FakeJobContext()
    monkeypatch.setattr(citations, "get_job_context", lambda: ctx)
    return ctx


async def test_match_payload_shape(fake_ctx: _FakeJobContext) -> None:
    retrieval_result = {
        "status": "match",
        "results": [
            {
                "source": "resume.pdf",
                "source_type": "resume",
                "section": "Experience",
                "text": "Led migration of the payments service.",
                "score": 0.81,
                "source_url": None,
            }
        ],
    }
    await citations.publish("turn_7", "payments experience", retrieval_result)

    assert len(fake_ctx.room.local_participant.published) == 1
    raw_payload, topic = fake_ctx.room.local_participant.published[0]
    assert topic == "citations"
    payload = json.loads(raw_payload)

    assert payload["type"] == "citations"
    assert payload["turn_id"] == "turn_7"
    assert payload["query"] == "payments experience"
    assert payload["status"] == "match"

    # CITATION_SPEC.md Sec4's example uses a "...Z" suffix; agent/citations.py
    # emits Python's own isoformat() ("+00:00") -- both are valid ISO8601 UTC
    # representations of the same instant, so this checks parseability and
    # UTC-ness rather than exact-matching the spec doc's illustrative string.
    parsed_ts = datetime.fromisoformat(payload["timestamp"])
    assert parsed_ts.utcoffset() is not None
    assert parsed_ts.utcoffset().total_seconds() == 0

    assert len(payload["sources"]) == 1
    source = payload["sources"][0]
    assert source["id"] == "cite_1"
    assert source["source"] == "resume.pdf"
    assert source["source_type"] == "resume"
    assert source["section"] == "Experience"
    assert source["excerpt"] == "Led migration of the payments service."
    assert source["score"] == 0.81
    assert source["url"] is None


async def test_no_match_payload_has_empty_sources(fake_ctx: _FakeJobContext) -> None:
    """FR-4.6: a refusal must never carry stale/implied sources."""
    retrieval_result = {"status": "no_match", "results": [], "instruction": "..."}
    await citations.publish("turn_8", "favourite food", retrieval_result)

    payload = json.loads(fake_ctx.room.local_participant.published[0][0])
    assert payload["status"] == "no_match"
    assert payload["sources"] == []


async def test_cite_ids_are_1_indexed_in_result_order(fake_ctx: _FakeJobContext) -> None:
    retrieval_result = {
        "status": "match",
        "results": [
            {
                "source": "a",
                "source_type": "resume",
                "section": "s1",
                "text": "t1",
                "score": 0.9,
                "source_url": None,
            },
            {
                "source": "b",
                "source_type": "context",
                "section": "s2",
                "text": "t2",
                "score": 0.7,
                "source_url": "https://example.com",
            },
        ],
    }
    await citations.publish("turn_1", "q", retrieval_result)

    payload = json.loads(fake_ctx.room.local_participant.published[0][0])
    assert [s["id"] for s in payload["sources"]] == ["cite_1", "cite_2"]
    assert payload["sources"][1]["url"] == "https://example.com"
