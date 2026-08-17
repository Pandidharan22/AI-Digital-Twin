"""Worker entrypoint.

Registers the LiveKit Agents worker, builds the AgentSession (STT -> LLM -> TTS
pipeline with VAD and turn detection), and dispatches TwinAgent into each room
automatically on visitor connection. Delivers the spoken greeting on join.

Covers: FR-1.4, FR-1.6, FR-2.1-2.3.
"""
