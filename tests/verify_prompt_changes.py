"""One-off behavioral verification for a system_prompt.md change (2026-08-23):
differentiated no_match refusals (personal/off-topic vs. undocumented-but-
career-related), a briefer false-premise correction, and length that flexes
to the question instead of a fixed "two to four sentences" rule.

Simulates TwinAgent's real flow end to end -- call 1 decides whether/how to
call search_my_background, the real agent.retrieval.retrieve() executes
(same production code path, real Supabase), call 2 generates the final
answer -- without a live LiveKit room, so this never risks a real visitor's
session landing on a throwaway worker. Prints full replies for a human to
read; not a pass/fail script, since prompt *style* isn't something to
assert on programmatically.

Run directly: uv run python -m tests.verify_prompt_changes
"""

import asyncio
import time

from google import genai
from google.genai import types

from agent import config, retrieval
from agent.twin_agent import _load_instructions

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

# One per prompt-change rationale: an off-topic/personal refusal, a
# false-premise correction, a genuine-depth question, and a simple one --
# matching what the owner specifically asked to see (Suite C's C1/C4 for
# regression, not re-run here since retrieval-layer behavior is unchanged).
QUESTIONS = [
    "What's your favourite pizza topping?",
    "You worked at Google, right?",
    "Tell me about the Self-Reflective RAG platform in detail -- what was the actual heuristic guardrail logic?",
    "Have you worked with Docker?",
]

PACE_SECONDS = 4


async def _run_one(client: genai.Client, system_instruction: str, question: str) -> None:
    cfg = types.GenerateContentConfig(system_instruction=system_instruction, tools=[TOOL])

    resp1 = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=[types.Content(role="user", parts=[types.Part(text=question)])],
        config=cfg,
    )
    part1 = resp1.candidates[0].content.parts[0]

    print(f"\n{'=' * 70}\nQ: {question}")

    if not part1.function_call:
        # Shouldn't happen per rule 1/1a, but report it plainly if it does.
        print(f"[no tool call] A: {resp1.text}")
        return

    query = part1.function_call.args.get("query", question)
    print(f"[tool call] query={query!r}")

    result = await retrieval.retrieve(query)
    print(f"[retrieval] status={result['status']}, results={len(result.get('results', []))}")

    resp2 = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=[
            types.Content(role="user", parts=[types.Part(text=question)]),
            types.Content(role="model", parts=[part1]),
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name="search_my_background", response=result
                        )
                    )
                ],
            ),
        ],
        config=cfg,
    )
    print(f"A: {resp2.text}")


async def main() -> None:
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    system_instruction = _load_instructions()

    for i, question in enumerate(QUESTIONS):
        await _run_one(client, system_instruction, question)
        if i < len(QUESTIONS) - 1:
            time.sleep(PACE_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
