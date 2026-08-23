"""Integration test: agent/retrieval.py's Suite A / Suite B contract
(TEST_PLAN.md Sec1), run against the real, live corpus.

Exercises agent/retrieval.py's actual retrieve() directly -- the real
production code path, not a parallel re-implementation -- per
BUILD_PLAN.md's original P3.5 description. Question lists are imported from
ingestion/tune_threshold.py rather than duplicated here, so this suite and
the threshold-sweep tool can never silently drift apart.

Marked `integration`: these do a real local embed (sentence-transformers)
and a real Supabase RPC call per question, so they need DATABASE_URL/
SUPABASE_* configured and take a few seconds. Run everything with
`uv run pytest`, or skip these specifically with `-m "not integration"`.

Three cases are marked xfail(strict=True) rather than left to fail
silently -- each is a real, understood, currently-accepted trade-off, not
an oversight:
  - CGPA: bge-small-en-v1.5's documented weakness anchoring on short
    acronyms/numbers inside longer passages (CLAUDE.md open item 4).
  - "hardest technical problem": the right chunk (context.md's "My
    strongest project") scores 0.51 -- real semantic relevance, but short
    of RETRIEVAL_THRESHOLD's 0.55 gate. Lowering the threshold to catch it
    would cost more Suite B false-accepts than TEST_PLAN.md Sec2's sweep
    found acceptable; rewording the chunk to game one query's score wasn't
    judged worth the risk of distorting content in the process. Diagnosed
    2026-08-23; left as a known trade-off, not silently ignored.
  - salary: TEST_PLAN.md Sec2's documented vocabulary-proximity false
    accept against an unrelated Loan-Eligibility README.
strict=True means if any of these starts passing (e.g. after a future
content or threshold change), the suite fails loudly instead of the fix
going unnoticed -- xfail is a tracked, falsifiable claim, not a permanent
excuse.
"""

import pytest

from agent.retrieval import retrieve
from ingestion.tune_threshold import SUITE_A, SUITE_B

_KNOWN_SUITE_A_GAPS = {
    "What's your CGPA?": "bge-small-en-v1.5's short-acronym/number weakness -- CLAUDE.md open item 4",
    "What was the hardest technical problem you've solved?": (
        "right chunk scores 0.51, just under RETRIEVAL_THRESHOLD's 0.55 gate -- "
        "a documented trade-off, not a content bug (docs/DEV_JOURNAL.md 2026-08-23)"
    ),
}

_KNOWN_SUITE_B_GAPS = {
    "What's your salary expectation?": (
        "documented vocabulary-proximity false accept vs. an unrelated "
        "Loan-Eligibility README -- TEST_PLAN.md Sec2"
    ),
}


def _suite_a_params():
    for query, keywords in SUITE_A:
        marks = []
        if query in _KNOWN_SUITE_A_GAPS:
            marks.append(pytest.mark.xfail(reason=_KNOWN_SUITE_A_GAPS[query], strict=True))
        yield pytest.param(query, keywords, marks=marks, id=query)


def _suite_b_params():
    for query in SUITE_B:
        marks = []
        if query in _KNOWN_SUITE_B_GAPS:
            marks.append(pytest.mark.xfail(reason=_KNOWN_SUITE_B_GAPS[query], strict=True))
        yield pytest.param(query, marks=marks, id=query)


@pytest.mark.integration
@pytest.mark.parametrize("query,keywords", list(_suite_a_params()))
async def test_suite_a_in_corpus_matches(query: str, keywords: list[str]) -> None:
    result = await retrieve(query)
    assert result["status"] == "match", f"expected a match for {query!r}, got no_match"
    haystack = " ".join(
        f"{r['source']} {r['section']} {r['text']}".lower() for r in result["results"]
    )
    assert any(kw.lower() in haystack for kw in keywords), (
        f"none of {keywords} found in top-{len(result['results'])} for {query!r}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("query", list(_suite_b_params()))
async def test_suite_b_out_of_corpus_refuses(query: str) -> None:
    result = await retrieve(query)
    assert result["status"] == "no_match", f"expected no_match for {query!r}, got a match"
    assert result["results"] == []
    assert "instruction" in result
