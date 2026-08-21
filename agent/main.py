"""Worker entrypoint.

Registers the LiveKit Agents worker, builds the AgentSession (STT -> LLM -> TTS
pipeline with VAD and turn detection), and dispatches TwinAgent into each room
automatically on visitor connection. Delivers the spoken greeting on join.

Covers: FR-1.4, FR-1.6, FR-2.1-2.3, FR-7.2.
"""

import logging

from livekit.agents import AgentServer, AgentSession, ChatMessage, JobContext, JobProcess
from livekit.agents.inference import TurnDetector
from livekit.plugins import deepgram, google, silero

from . import config
from .retrieval import _match_sync
from .twin_agent import TwinAgent

logger = logging.getLogger("voice_twin.agent")

# FR-7.2: spoken when the LLM's own retry budget (livekit-plugins-google's
# built-in backoff -- FR-7.1) is exhausted, so a rate limit or outage reads as
# an apology, not a silent drop back to "listening". Plain speakable text,
# same voice rules as everything else that reaches TTS.
LLM_FALLBACK_MESSAGE = (
    "Sorry, I'm having trouble reaching my language model right now. "
    "Please try again in a moment."
)


def _prewarm(proc: JobProcess) -> None:
    """Runs once per job-runner process, before it accepts any room -- the
    standard LiveKit Agents hook for paying one-time model-load costs up
    front instead of on a visitor's first real turn.

    LiveKit spawns a fresh process per room for isolation, so retrieval.py's
    embedding model and Supabase client (both lazily created on first use)
    were otherwise getting loaded during whichever turn happened to be the
    first grounded question of the conversation -- observed live as a
    13.79s e2e_latency spike on an otherwise-4s turn (docs/DEV_JOURNAL.md,
    2026-08-21). Reuses retrieval.py's own sync helper -- the exact code
    path a real query takes -- rather than duplicating the embed+RPC logic
    here. Discarded on purpose: this is a throwaway query whose only job is
    to warm the model cache (embed_query's @lru_cache) and the Supabase
    connection, not to produce a usable result.
    """
    _match_sync("warmup")


# CLI auto-discovery (livekit/agents/cli/discover.py) requires this exact
# variable name -- app, server, or agent, in that priority order. See
# docs/SDK_NOTES.md Sec4.
server = AgentServer(setup_fnc=_prewarm)


# No agent_name: a non-empty agent_name switches on "explicit dispatch," where
# the SDK's own docstring says "jobs will not be dispatched to rooms
# automatically." FR-1.4 requires automatic dispatch on visitor connection
# with no manual dispatch step, so this must stay at the "" default.
@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()
    logger.info("[room=%s] job started, worker connected", ctx.room.name)

    session = AgentSession(
        stt=deepgram.STT(),
        llm=google.LLM(model=config.GEMINI_MODEL, api_key=config.GEMINI_API_KEY),
        tts=deepgram.TTS(),
        vad=silero.VAD.load(),
        turn_handling={"turn_detection": TurnDetector()},
    )

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev) -> None:
        logger.info(
            "[room=%s] agent_state: %s -> %s", ctx.room.name, ev.old_state, ev.new_state
        )

    @session.on("user_state_changed")
    def _on_user_state_changed(ev) -> None:
        logger.info(
            "[room=%s] user_state: %s -> %s", ctx.room.name, ev.old_state, ev.new_state
        )

    @session.on("user_input_transcribed")
    def _on_transcript(ev) -> None:
        if ev.is_final:
            logger.info("[room=%s] transcript (final): %r", ctx.room.name, ev.transcript)

    @session.on("error")
    def _on_error(ev) -> None:
        # ev.error.recoverable is False only on the LLMError emitted right
        # before the framework gives up on a generation attempt (see
        # livekit/agents/llm/llm.py's _main_task: every retried attempt emits
        # recoverable=True first, and only the final, exhausted attempt emits
        # recoverable=False) -- so this fires once per genuinely failed turn,
        # not once per retry. AgentSession itself only force-closes the
        # session after 3 consecutive unrecoverable errors (its own
        # max_unrecoverable_errors default); below that it does nothing user-
        # facing on its own, which is the exact silent-hang gap a live 429
        # exposed (docs/DEV_JOURNAL.md, 2026-08-20). FR-7.3 (vector store
        # unavailability) and FR-7.4 (structured stage-failure logging) are
        # separate requirements, not covered by this handler.
        if ev.error.type == "llm_error" and not ev.error.recoverable:
            logger.error(
                "[room=%s] LLM retries exhausted, speaking fallback: %s",
                ctx.room.name,
                ev.error.error,
            )
            session.say(LLM_FALLBACK_MESSAGE)

    @session.on("conversation_item_added")
    def _on_conversation_item(ev) -> None:
        # `metrics_collected` (the event livekit/agents/metrics/base.py
        # documents) is deprecated as of this installed version -- confirmed
        # live via a runtime DeprecationWarning during Phase 1 testing, not
        # assumed. The current source of per-turn latency is
        # ChatMessage.metrics, attached to each item as the turn completes.
        # Covers structured pipeline logging (P1.1) and the latency baseline
        # (P1.3, NFR-1): e2e_latency is exactly NFR-1.1's "end-of-utterance to
        # first audio byte".
        item = ev.item
        if not isinstance(item, ChatMessage):
            return

        logger.info("[room=%s] turn (%s): %r", ctx.room.name, item.role, item.text_content)

        m = item.metrics
        if m:
            logger.info(
                "[room=%s] turn metrics: transcription_delay=%s end_of_turn_delay=%s "
                "llm_ttft=%s tts_ttfb=%s e2e_latency=%s",
                ctx.room.name,
                m.get("transcription_delay"),
                m.get("end_of_turn_delay"),
                m.get("llm_node_ttft"),
                m.get("tts_node_ttfb"),
                m.get("e2e_latency"),
            )

    # Phase 3: the real grounded persona (CITATION_SPEC.md Sec5) replaces
    # Phase 1's trivial no-persona placeholder -- retrieval, owner name, and
    # the search_my_background tool are all live from here on.
    agent = TwinAgent()

    await session.start(agent=agent, room=ctx.room)
    logger.info("[room=%s] session started, sending greeting", ctx.room.name)

    # No factual claim in the greeting itself, so the prompt's own rule ("do
    # not call the search tool for greetings") keeps this from triggering a
    # retrieval + citation publish before the visitor has asked anything.
    session.generate_reply(
        instructions=(
            f"Greet the visitor in one short sentence as {config.OWNER_NAME}'s voice "
            "twin, and invite them to ask about your background."
        )
    )
