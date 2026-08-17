"""Worker entrypoint.

Registers the LiveKit Agents worker, builds the AgentSession (STT -> LLM -> TTS
pipeline with VAD and turn detection), and dispatches TwinAgent into each room
automatically on visitor connection. Delivers the spoken greeting on join.

Covers: FR-1.4, FR-1.6, FR-2.1-2.3.
"""

import logging

from livekit.agents import Agent, AgentServer, AgentSession, ChatMessage, JobContext
from livekit.agents.inference import TurnDetector
from livekit.plugins import deepgram, google, silero

from . import config

logger = logging.getLogger("voice_twin.agent")

# CLI auto-discovery (livekit/agents/cli/discover.py) requires this exact
# variable name -- app, server, or agent, in that priority order. See
# docs/SDK_NOTES.md Sec4.
server = AgentServer()


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

    # Trivial, no-persona prompt for this phase: no retrieval, no owner name,
    # no tools. The real TwinAgent (CITATION_SPEC.md Sec5) arrives in Phase 3.
    agent = Agent(
        instructions=(
            "You are a friendly, concise voice assistant helping verify that an "
            "audio pipeline works end to end. Keep replies to one or two short "
            "sentences. Never use markdown, bullet points, asterisks, or emoji "
            "-- your words are spoken aloud, not displayed as text."
        )
    )

    await session.start(agent=agent, room=ctx.room)
    logger.info("[room=%s] session started, sending greeting", ctx.room.name)

    session.generate_reply(
        instructions="Greet the user in one short sentence and say you're ready to chat."
    )
