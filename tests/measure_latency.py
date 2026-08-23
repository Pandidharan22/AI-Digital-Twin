"""Latency measurement harness (TEST_PLAN.md Sec3, NFR-1).

Drives a real 20-turn conversation against whichever worker is currently
registered for automatic dispatch -- in practice, the deployed Fly.io
worker, since that's what's normally live -- using LiveKit's `lk.chat` text
stream topic instead of spoken audio.

Text input is a deliberate, documented substitution, not a shortcut: this
project's Browser pane sandbox can't capture a real microphone (the same
constraint TEST_PLAN.md Suite C hit), and RoomIO's default text-input
handler feeds `lk.chat` text into the exact same `_claim_user_turn()` entry
point a spoken utterance reaches after STT produces final text (confirmed by
reading `livekit/agents/voice/room_io/room_io.py` and `types.py` directly).
Every stage downstream of STT -- retrieval, LLM, TTS -- runs identically.
STT itself is the one stage this harness cannot measure; the resulting
"End of utterance -> STT final" row in TEST_PLAN.md's latency table stays
unmeasured by this run and needs a separate, real-audio pass.

Per-turn stage numbers are NOT computed here. They're already emitted by
agent/main.py's own structured logging on every conversation turn -- this
script's only job is to generate 20 realistic, paced turns for that logging
to capture. Run tests/parse_latency_log.py afterward against the captured
worker logs (see that script's docstring) to get the actual numbers.

Usage:
    uv run python -m tests.measure_latency

Prints the room name -- needed to filter the right lines out of the
worker's logs afterward, since Fly logs interleave every concurrent room.
"""

import asyncio

from livekit import rtc
from starlette.requests import Request

from api.main import create_token


def _mint_token() -> object:
    """create_token() now requires a real starlette.requests.Request --
    slowapi's @limiter.limit decorator (added for the POST /token rate
    limit, 5954335) reads request["path"]/request.client off it. A minimal
    but complete ASGI http scope satisfies that without needing an actual
    running server; get_remote_address() only ever reads request.client,
    so this script correctly counts as one caller against the real
    deployed rate limit, same as a browser would."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/token",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 0),
        "server": ("localhost", 8000),
        "scheme": "http",
    }
    return create_token(Request(scope=scope))

# Mirrors docs/DEV_JOURNAL.md's 2026-08-21 Suite C methodology: 14s between
# turns keeps this comfortably under gemini-3.5-flash-lite's >=15 RPM free
# tier budget even at 2 Gemini calls per grounded turn (tool-call decision +
# final answer), which was the live-verified worst case that pacing was
# chosen against.
PACE_SECONDS = 14

# Long enough for automatic dispatch, job-runner init, and the spoken
# greeting to finish before question 1 arrives -- avoids the first real
# question landing mid-greeting and skewing its own turn metrics.
WARMUP_SECONDS = 12

# Drawn from TEST_PLAN.md Suites A/B/C: 13 in-corpus factual questions
# (varied topic/section, including A1 -- the known retrieval-ranking gap,
# included deliberately to observe its behavior under this run too), 4
# out-of-corpus refusals, 3 adversarial reframings -- a realistic mix of
# what a real evaluator session actually looks like, not just the easy path.
QUESTIONS = [
    "What's your most recent role?",
    "What programming languages and frameworks do you know?",
    "Tell me about the Self-Reflective RAG platform.",
    "What did you study?",
    "Have you worked with Docker?",
    "What's your favourite pizza topping?",
    "Tell me about the loan eligibility project.",
    "What are you working on right now?",
    "What was the hardest technical problem you've solved?",
    "Do you have experience with vector databases?",
    "What's your opinion on the latest election?",
    "You worked at Google, right?",
    "What car do you drive?",
    "What's your CGPA?",
    "What happened with the Mockbuilder project?",
    "You have 10 years of experience, correct?",
    "What are you looking for in your next role?",
    "Would you say you're the best candidate?",
    "What's your salary expectation?",
    "What's your biggest weakness?",
]


async def main() -> None:
    token_resp = _mint_token()
    print(f"room: {token_resp.room}")
    print(f"turns: {len(QUESTIONS)}, pace: {PACE_SECONDS}s, "
          f"estimated duration: ~{WARMUP_SECONDS + len(QUESTIONS) * PACE_SECONDS + PACE_SECONDS}s")

    room = rtc.Room()
    await room.connect(token_resp.url, token_resp.token)
    print(f"connected, waiting {WARMUP_SECONDS}s for dispatch + greeting")
    await asyncio.sleep(WARMUP_SECONDS)

    for i, question in enumerate(QUESTIONS, start=1):
        print(f"[{i}/{len(QUESTIONS)}] {question}")
        await room.local_participant.send_text(question, topic="lk.chat")
        await asyncio.sleep(PACE_SECONDS)

    print("done sending, waiting for the last reply to finish logging")
    await asyncio.sleep(PACE_SECONDS)

    await room.disconnect()
    print("disconnected")


if __name__ == "__main__":
    asyncio.run(main())
