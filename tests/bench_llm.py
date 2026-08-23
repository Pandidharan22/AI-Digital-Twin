"""Direct Gemini API benchmark for LLM latency optimization (TEST_PLAN.md
Sec3, item 3 on the post-launch to-do list).

tests/measure_latency.py measured the *pipeline's* llm_ttft (median 1066ms,
p95 1276ms, ~2x the NFR-1.4 target) but only for the second of two
sequential Gemini calls a grounded turn makes (the tool-decision call has
no ChatMessage/metrics of its own in livekit-agents' event model -- checked
directly in chat_context.py: FunctionCall items carry no .metrics field).
This script calls the same google-genai SDK livekit-plugins-google wraps
directly, real system prompt, real tool schema shape, real model, to:

1. See the tool-decision call's own TTFT, invisible in the pipeline's own
   metrics.
2. A/B real candidate levers instead of guessing: thinking_level (Gemini's
   own docs, fetched live, say gemini-3.5-flash-lite already defaults to
   "minimal" -- worth confirming empirically, not just trusting the docs
   page), and system prompt length.

Not a pytest test -- a one-shot diagnostic, matching tests/measure_latency.py's
own role. Run directly: uv run python -m tests.bench_llm
"""

import statistics
import time

from google import genai
from google.genai import types

from agent import config
from agent.twin_agent import _load_instructions

MODEL = config.GEMINI_MODEL
TRIALS = 6
# Same pacing reasoning as tests/measure_latency.py: gemini-3.5-flash-lite's
# free-tier budget is >=15 RPM (CLAUDE.md); ~4s between calls keeps every
# variant's sequential trials comfortably under that regardless of how fast
# any individual response comes back.
PACE_SECONDS = 4

TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_my_background",
            description=(
                "Search the owner's documented background for information relevant "
                "to the query. Call this before making ANY factual claim about the "
                "owner's experience, skills, projects, education, or history."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {"query": {"type": "STRING"}},
                "required": ["query"],
            },
        )
    ]
)

USER_QUESTION = "What's your most recent role?"
TOOL_ARGS = {"query": "most recent role"}
# A real retrieved chunk's shape/length, not a placeholder -- matches
# agent/retrieval.py's actual contract (a dict with status/results).
TOOL_RESULT = {
    "status": "match",
    "results": [
        {
            "source": "AI Engineer Resume.pdf",
            "section": "Most Recent Role — Freelance Software Developer",
            "text": (
                "What I studied: ... Most recent role: Freelance Software Developer. "
                "Built client-facing production web experiences and applied AI "
                "systems, translating architecture design into deployable "
                "solutions. Collaborated directly with stakeholders to translate "
                "requirements into working systems under short delivery cycles."
            ),
            "score": 0.70,
        }
    ],
}


def _call1_contents() -> list[types.Content]:
    return [types.Content(role="user", parts=[types.Part(text=USER_QUESTION)])]


def _real_function_call_part(client: genai.Client, system_instruction: str) -> types.Part:
    """One real (non-streamed, unbenchmarked) call1 request, to get a real
    function_call Part -- Gemini 3 requires a real thought_signature on it
    for multi-turn context (confirmed live: a fabricated function_call Part
    with no signature gets a hard 400 INVALID_ARGUMENT, not a soft warning).
    livekit-plugins-google already threads real thought_signatures through
    for production traffic (confirmed by reading llm.py directly -- see
    docs/DEV_JOURNAL.md's 2026-08-23 entry); this mirrors that for the
    benchmark's call2 variants."""
    cfg = types.GenerateContentConfig(system_instruction=system_instruction, tools=[TOOL])
    resp = client.models.generate_content(model=MODEL, contents=_call1_contents(), config=cfg)
    part = resp.candidates[0].content.parts[0]
    if not part.function_call:
        raise RuntimeError("Model didn't call the tool on the priming request -- can't build call2.")
    return part


def _call2_contents(function_call_part: types.Part) -> list[types.Content]:
    return [
        types.Content(role="user", parts=[types.Part(text=USER_QUESTION)]),
        types.Content(role="model", parts=[function_call_part]),
        types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        name="search_my_background", response=TOOL_RESULT
                    )
                )
            ],
        ),
    ]


def _time_ttft(client: genai.Client, system_instruction: str, contents, thinking_level: str | None) -> float:
    config_kwargs = dict(system_instruction=system_instruction, tools=[TOOL])
    if thinking_level is not None:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
    cfg = types.GenerateContentConfig(**config_kwargs)

    start = time.perf_counter()
    stream = client.models.generate_content_stream(model=MODEL, contents=contents, config=cfg)
    for chunk in stream:
        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
            return time.perf_counter() - start
    return time.perf_counter() - start


def _summarize(label: str, samples: list[float]) -> None:
    ms = sorted(s * 1000 for s in samples)
    median = statistics.median(ms)
    p95 = ms[min(len(ms) - 1, round(0.95 * (len(ms) - 1)))]
    print(f"{label:<38} n={len(ms):<3} median={median:>6.0f}ms  p95={p95:>6.0f}ms  "
          f"min={ms[0]:>6.0f}ms  max={ms[-1]:>6.0f}ms")


def main() -> None:
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    system_instruction = _load_instructions()
    short_instruction = "You are a helpful voice assistant. Keep answers brief."

    print(f"Model: {MODEL}, {TRIALS} trials per variant\n")

    print("Priming: one real call1 request to get a valid thought_signature for call2...")
    fc_part = _real_function_call_part(client, system_instruction)
    time.sleep(PACE_SECONDS)

    variants = [
        ("call1 (tool-decision), real prompt, default thinking", lambda: _call1_contents(), system_instruction, None),
        ("call2 (final answer), real prompt, default thinking", lambda: _call2_contents(fc_part), system_instruction, None),
        ("call2, real prompt, thinking_level=minimal (explicit)", lambda: _call2_contents(fc_part), system_instruction, "minimal"),
        ("call2, SHORT prompt, default thinking", lambda: _call2_contents(fc_part), short_instruction, None),
    ]

    for label, contents_fn, instruction, thinking_level in variants:
        samples = []
        for i in range(TRIALS):
            samples.append(_time_ttft(client, instruction, contents_fn(), thinking_level))
            time.sleep(PACE_SECONDS)
        _summarize(label, samples)


if __name__ == "__main__":
    main()
