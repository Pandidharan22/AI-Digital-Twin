# SDK Notes — LiveKit Agents (verified against the installed package)

**Verified 2026-08-17** by reading the actual installed source under `.venv/Lib/site-packages/livekit/`
and running real imports/`inspect.signature()` calls against it — not from memory, not
from a tutorial. Per `CLAUDE.md` rule #2 and `CLAUDE_CODE_PROMPTS.md` P0.2. If a future
`uv sync` bumps these versions, re-verify before trusting anything below.

## Installed versions

| Package | Version |
|---|---|
| `livekit-agents` | 1.6.10 |
| `livekit` (rtc bindings) | 1.1.14 |
| `livekit-api` | 1.2.0 |
| `livekit-plugins-deepgram` | 1.6.10 |
| `livekit-plugins-google` | 1.6.10 |
| `livekit-plugins-silero` | 1.6.10 |
| Python | 3.12.10 |

---

## 0. The big thing tutorials get wrong at this version

Most "LiveKit Agents 1.0" tutorials (correctly) tell you `VoicePipelineAgent` was
replaced by `AgentSession`. What they don't mention — because it's newer than most of
them — is that **the entrypoint-registration pattern has changed again** since then.

The classic pattern:

```python
from livekit.agents import cli, WorkerOptions

def entrypoint(ctx: JobContext): ...

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

still runs (the installed `cli.run_app` accepts `AgentServer | WorkerOptions`), but its
own docstring says plainly:

> "Run the agent via the (deprecated) rich Python CLI. [...] being phased out in favor
> of the LiveKit CLI (`lk agent ...`) and the thin interface in
> `livekit.agents.__main__`."

The current pattern is `AgentServer` + a decorator. See Sec4.

---

## 1. Session and agent primitives

| Concept | Real import | Notes |
|---|---|---|
| Agent definition | `from livekit.agents import Agent` | `livekit/agents/voice/agent.py`. Subclass it. |
| Pipeline/session | `from livekit.agents import AgentSession` | `livekit/agents/voice/agent_session.py` |
| Per-job context | `from livekit.agents import JobContext` | `livekit/agents/job.py`. Passed into your entrypoint. |
| Context from anywhere | `from livekit.agents import get_job_context` | Context-var accessor — see callout below. |

**`Agent.__init__`** (trimmed to what matters here):

```python
Agent(
    *,
    instructions: str,
    tools: list[llm.Tool] | None = None,
    stt=NOT_GIVEN, vad=NOT_GIVEN, llm=NOT_GIVEN, tts=NOT_GIVEN,   # per-agent override of session defaults
    turn_handling=NOT_GIVEN,
    chat_ctx=NOT_GIVEN,
)
```

**`AgentSession.__init__`** (trimmed):

```python
AgentSession(
    *,
    stt=NOT_GIVEN, vad=NOT_GIVEN, llm=NOT_GIVEN, tts=NOT_GIVEN,
    turn_handling=NOT_GIVEN,       # replaces the older separate min/max_endpointing_delay + turn_detection kwargs
    tools=NOT_GIVEN,
    tts_text_transforms=NOT_GIVEN, # see Sec6 — defaults matter for FR-2.6
    userdata=NOT_GIVEN,
)
```

**`AgentSession.start`** (trimmed):

```python
await session.start(
    agent: Agent,
    *,
    room: rtc.Room = NOT_GIVEN,       # pass ctx.room here
    room_options=NOT_GIVEN,
)
```

**Speaking without waiting for user input** (for the FR-1.6 greeting):

```python
session.say(text: str) -> SpeechHandle                                  # speaks fixed text
session.generate_reply(*, instructions: str = NOT_GIVEN) -> SpeechHandle # LLM composes it
```

Both are synchronous calls that return a `SpeechHandle` (the speech runs in the
background); `generate_reply(instructions=...)` is the better fit for the greeting since
the prompt already governs voice, so the greeting stays in the same voice/style.

---

## 2. Defining function tools

`from livekit.agents import function_tool` (real home: `livekit/agents/llm/tool_context.py`,
re-exported at package root).

Two attachment styles, both work:

```python
# Style A — free function, attached explicitly
@function_tool
async def search_my_background(context: RunContext, query: str) -> dict:
    """Search the owner's documented background for information relevant to the query."""
    ...

agent = Agent(instructions=..., tools=[search_my_background])

# Style B — method on an Agent subclass, auto-discovered
class TwinAgent(Agent):
    @function_tool
    async def search_my_background(self, context: RunContext, query: str) -> dict:
        """Search the owner's documented background..."""
        ...
```

Style B works because `Agent.__init__` runs
`self._tools = [*tools, *find_function_tools(self)]` — it scans the instance for
`@function_tool`-decorated methods automatically. No manual registration needed.

**The docstring is not decoration — it's the tool description the LLM sees.** The
decorator runs `docstring_parser.parse_from_object(func)` and uses the parsed
description unless you pass `description=` explicitly. This is exactly why
`CITATION_SPEC.md` Sec3's `search_my_background` example has that specific docstring —
it's not a comment, it's the API contract text the LLM reads to decide when to call the
tool.

**`RunContext`** (`from livekit.agents import RunContext`, defined in
`livekit/agents/voice/events.py`): the first parameter of a tool method. Gives:
- `context.session` → the running `AgentSession`
- `context.userdata` → whatever typed userdata the session was constructed with
- `context.speech_handle`, `context.function_call` → metadata about the in-flight turn

---

## 3. Publishing to the data channel (citations)

The publish call itself lives in the `livekit` (rtc bindings) package, not
`livekit-agents`:

```python
# livekit/rtc/participant.py
async def publish_data(
    self,
    payload: bytes | str,
    *,
    reliable: bool = True,
    destination_identities: list[str] = [],
    topic: str = "",
) -> None
```

Called as `await room.local_participant.publish_data(...)`. `payload` must be `str` or
`bytes` — for the citation JSON payload from `CITATION_SPEC.md` Sec4, that's
`json.dumps(payload)`, and `topic="citations"` per spec.

**Getting the room without threading it through every constructor:** `AgentSession`
does not expose a public `.room` property. The clean way to reach it from inside
`agent/citations.py` — called from within the `search_my_background` tool, which only
has `RunContext`, not `JobContext` — is:

```python
from livekit.agents import get_job_context

ctx = get_job_context()          # context-var lookup; works anywhere inside the running job
await ctx.room.local_participant.publish_data(
    json.dumps(payload), topic="citations"
)
```

This is a real, non-obvious finding worth calling out: `get_job_context()` reads a
`contextvars.ContextVar`, so it works even deep inside a tool call with no explicit
context threading — no need to pass `JobContext` into `TwinAgent.__init__` by hand.

---

## 4. Worker entrypoint registration (the current pattern)

```python
# agent/main.py
from livekit.agents import AgentServer, JobContext, AgentSession
from livekit.plugins import deepgram, google, silero

server = AgentServer()          # variable MUST be named app, server, or agent — see below

@server.rtc_session(agent_name="voice-twin")
async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()          # required before session.start(); subscribes to tracks

    session = AgentSession(
        stt=deepgram.STT(),
        llm=google.LLM(),
        tts=deepgram.TTS(),
        vad=silero.VAD.load(),   # note: .load(), not VAD() — see Sec5
    )
    await session.start(agent=TwinAgent(), room=ctx.room)
    session.generate_reply(instructions="Greet the user briefly.")
```

**Discovery matters.** `livekit.agents.cli.discover.get_app_name()` looks for a
module-level object that `isinstance(obj, AgentServer)` under the names `app`, `server`,
`agent`, in that priority order, then falls back to scanning every module-level name.
Name the variable one of those three or the CLI can't find it. Default file discovery
(`get_default_path`) looks for `main.py`, `app.py`, `agent.py`, `app/main.py`, etc. —
`agent/main.py` matches.

**Running it:**

```bash
uv run python -m livekit.agents start agent/main.py   # connects to LiveKit Cloud, production-style
uv run python -m livekit.agents console --connect-addr <addr>  # local console/TCP testing
```

(The exact `console` flags need confirming once we actually run this in Phase 1 —
flagged as a Phase 1 follow-up below.)

---

## 5. Plugin import paths and verified defaults

Confirmed by direct import + `inspect.signature()`, not the docs site:

| Plugin | Import | Constructor | Verified default |
|---|---|---|---|
| Deepgram STT | `from livekit.plugins import deepgram` | `deepgram.STT(*, model=..., ...)` | `model="nova-3"` |
| Deepgram TTS | `from livekit.plugins import deepgram` | `deepgram.TTS(*, model=..., ...)` | `model="aura-2-andromeda-en"` |
| Gemini LLM | `from livekit.plugins import google` | `google.LLM(*, model=..., ...)` | `model="gemini-2.5-flash"` — **compiled-in default, but see the callout below: this specific value 404s live** |
| Silero VAD | `from livekit.plugins import silero` | `silero.VAD.load(...)` | **classmethod, not a plain constructor** — `VAD()` directly will not work |

All four read their API key from the matching env var by default
(`api_key: NotGivenOr[str] = NOT_GIVEN` falls back to `DEEPGRAM_API_KEY` /
`GOOGLE_API_KEY`-equivalent internally) — explicit `api_key=` args are only needed to
override that.

**Confirmed gotcha for `agent/config.py`:** `google.LLM` resolves its key as
`api_key if given else os.environ.get("GOOGLE_API_KEY")` (`livekit/plugins/google/llm.py`
line 196) — it reads `GOOGLE_API_KEY`, **not** `GEMINI_API_KEY`. Our `.env` (per
`DEPLOYMENT.md`) uses `GEMINI_API_KEY`. Left as-is, `google.LLM()` called with no
`api_key` argument will raise "API key is required" even though `.env` has a perfectly
valid key under a different name. `agent/config.py` needs to either pass
`api_key=os.environ["GEMINI_API_KEY"]` explicitly when constructing `google.LLM(...)`,
or set `os.environ["GOOGLE_API_KEY"]` from `GEMINI_API_KEY` at startup. Passing it
explicitly is cleaner — it keeps the env var naming in `.env` matching the rest of this
project's docs without silently duplicating it into a second env var name.

**Second confirmed gotcha, found during live Phase 1 testing:** the plugin's compiled-in
default model, `gemini-2.5-flash`, returns a live `HTTP 404` —
`"This model models/gemini-2.5-flash is no longer available to new users"` — when
actually called with `generateContent`, even though it still appears in the `/models`
listing endpoint (listing != eligibility). Confirmed by direct `curl` against
Google's API, not the plugin's own error message alone. `gemini-2.5-flash-lite` is
also retired the same way. `gemini-flash-latest` — a rolling alias Google maintains to
whatever the current recommended flash model is — works (verified via a real
`generateContent` 200, resolving to `gemini-3.7-flash` at time of writing) and is what
`agent/config.py`'s `GEMINI_MODEL` default now uses instead, specifically to avoid
repeating this breakage the next time a pinned version number gets retired.

---

## 6. Built-in behavior relevant to this project's requirements

- **`AgentSession`'s `tts_text_transforms` defaults to `["filter_markdown", "filter_emoji"]`**
  (`DEFAULT_TTS_TEXT_TRANSFORMS` in `agent_session.py`). The framework already strips
  markdown and emoji before audio synthesis by default. This *reinforces* — doesn't
  replace — the prompt-level "plain speakable text" rule in `CITATION_SPEC.md` Sec5
  (FR-2.6): it's a second, structural layer catching what the prompt rule misses, the
  same defense-in-depth pattern the citation system uses (`CITATION_SPEC.md` Sec2).
- **`turn_handling` supersedes the older separate kwargs.** `min_endpointing_delay`,
  `max_endpointing_delay`, `turn_detection`, `allow_interruptions`, etc. still exist as
  constructor params but are marked deprecated (`@deprecate_params(..., target_version="v2.0")`)
  and auto-migrated into a `TurnHandlingOptions` dict internally. Write new code against
  `turn_handling=TurnHandlingOptions(...)` directly rather than the individual kwargs.

---

## 7. Open follow-ups for Phase 1

- `livekit-plugins-turn-detector` is not installed. SRS FR-2.2 requires *semantic* turn
  detection, not just VAD endpointing — this package (or an equivalent `turn_handling`
  config) needs adding before FR-2.2 is actually satisfied. Flagged previously in
  `DEV_JOURNAL.md`'s 2026-08-17 venv/deps entry; repeating here since it's the SDK
  surface this note is about.
- Confirm the exact `console` subcommand flags for local testing without a deployed
  LiveKit room, once Phase 1 actually runs the worker.
