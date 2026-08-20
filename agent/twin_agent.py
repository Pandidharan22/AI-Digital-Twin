"""TwinAgent: the Agent subclass carrying the system prompt and the search_my_background
function tool.

Owns per-turn orchestration: deciding when a factual claim requires retrieval,
enforcing the grounding contract (CITATION_SPEC.md Sec5), and refusing gracefully
on no_match.

Covers: FR-3.1, FR-3.4-3.7.
"""

from pathlib import Path

from livekit.agents import Agent, RunContext, function_tool

from . import citations, config, retrieval

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"


def _load_instructions() -> str:
    """Read the grounding + voice contract from prompts/system_prompt.md and
    substitute the owner's name. The prompt text itself lives in that file, not
    here, so it stays editable without touching code (see CLAUDE.md's Key
    Files table)."""
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("[NAME]", config.OWNER_NAME)


class TwinAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=_load_instructions())

    @function_tool
    async def search_my_background(self, context: RunContext, query: str) -> dict:
        """
        Search the owner's documented background for information relevant to the query.
        Call this before making ANY factual claim about the owner's experience,
        skills, projects, education, or history.
        """
        result = await retrieval.retrieve(query)

        # Published before returning to the LLM, so the source cards are on
        # screen before the LLM has generated a word of the spoken reply
        # (ADR-005, FR-4.1). context.speech_handle.id is a real per-turn
        # identifier the SDK already assigns -- reused as turn_id rather than
        # inventing a parallel counter.
        await citations.publish(context.speech_handle.id, query, result)

        return result
