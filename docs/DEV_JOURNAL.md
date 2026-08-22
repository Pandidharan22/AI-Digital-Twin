# Dev Journal — Voice Twin

## About this journal

This is a dated log of every verified, committed step in the build — what was decided,
what was built or changed, what was removed, and **why**. It exists to make interview
prep painless: months from now, "why did you choose X" should have an answer already
written down, not require reconstructing memory from a diff.

**Protocol** (see also `CLAUDE.md` → Working style, where this is the canonical
source of truth):

1. Do the work.
2. Verify it — run it, check output, confirm no secrets before staging.
3. Commit the work on its own.
4. Write the journal entry for that step here — detailed, in plain language, explaining
   the underlying concepts and not just what changed.
5. Commit the journal entry **separately**, in its own commit.

Work commits and journal commits are never bundled. Git history should read as two
parallel tracks: "the change" and "the reflection on the change."

Entries are appended in chronological order — oldest at the top, most recent at the
bottom. New entries always go at the **end** of the file.

---

## 2026-08-16 — Phase 0: Documentation review, credentials, and repo initialization

**What happened**

- Read the complete documentation set (`PRD.md`, `SRS.md`, `ARCHITECTURE.md`,
  `CITATION_SPEC.md`, `DATA_INGESTION.md`, `BUILD_PLAN.md`, `TEST_PLAN.md`,
  `DEPLOYMENT.md`, `CLAUDE_CODE_PROMPTS.md`) plus `CLAUDE.md` and `README.md` to
  understand the full spec before writing any code.
- Obtained credentials for all five required services and populated `.env`:
  - **LiveKit Cloud** — `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`. This is
    the WebRTC transport layer (the "SFU" — selective forwarding unit — that routes
    audio between the browser and the agent worker).
  - **Deepgram** — `DEEPGRAM_API_KEY`. One key covers both speech-to-text (Nova-3) and
    text-to-speech (Aura-2).
  - **Google AI Studio** — `GEMINI_API_KEY`, for the Gemini Flash LLM.
  - **Supabase** — `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and a database connection
    string. Enabled the `vector` extension (pgvector), which adds a vector column type
    and similarity-search operators to Postgres — this is what makes semantic search
    over document chunks possible without standing up a separate vector database
    product. Retrieved the **service role key** (not the `anon` key) — the service role
    key bypasses Postgres row-level security, which is why it's only ever used
    server-side (ingestion job, agent worker) and never shipped to the frontend.
  - **GitHub** — a **fine-grained PAT** scoped to "Public Repositories (read-only)".
    Fine-grained tokens (as opposed to older classic tokens) let access be scoped down
    to exactly what's needed instead of a blanket `repo` scope — here, read-only access
    to public repos is all the ingestion job needs to pull README content and repo
    metadata.
- **Follow-ups flagged, not yet fixed:** the Supabase connection string is currently
  named `SUPABASE_CONNECTION_STRING` in `.env` but every doc expects `DATABASE_URL` —
  needs renaming before Phase 2 ingestion code is written. The Gemini key's format
  (`AQ.Ab8RN6...`) doesn't match the typical `AIzaSy...` pattern for AI Studio keys and
  should be double-checked against the AI Studio dashboard.
- Created `.gitignore` (Python, Node, `.env`, OS/IDE cruft) — **before** any `git add`,
  since `.env` already existed on disk, untracked, and needed to be excluded before it
  could ever be staged.
- Verified exclusion with `git check-ignore -v .env` — confirmed matched by
  `.gitignore:2:.env`.
- Created `.env.example` with the same keys as `.env` but blank values, per SRS
  NFR-3.3 — this is what lets someone clone the repo and know exactly what to fill in
  without ever seeing a real secret.
- Scanned every file about to be committed for secret-shaped strings (`AIza`,
  `github_pat_`, JWT-looking strings, PEM headers) before staging — all clean.
- Made the first commit (`ef5b150`): the full docs set, `CLAUDE.md`, `README.md`,
  `.gitignore`, `.env.example`. `.env` itself was never staged.

**Why**

The project's non-negotiable rule #1 is "never hardcode secrets, everything through
environment variables, `.env` is gitignored, checked before every commit" (`CLAUDE.md`).
With no `.gitignore` present yet and `.env` already sitting in the working directory,
the very first git operation in this repo's life was the highest-risk moment for a
secret to land in history by accident — so gitignore-then-verify came before anything
else, including the docs commit.

**Decisions made**

- Confirmed all Phase 0 credentials are in place — no further account sign-ups needed
  for now.
- Adopted the full `.env.example` key set from `DEPLOYMENT.md` rather than only the
  keys currently filled, so the file documents the entire eventual configuration
  surface (including `RETRIEVAL_THRESHOLD`, `EMBEDDING_MODEL`, `OWNER_NAME`, etc. that
  get filled in during later phases) rather than growing piecemeal.

**Verification**

- `git check-ignore -v .env` → matched, confirmed excluded.
- `grep` for secret patterns across all staged files → zero matches.
- `git status` after staging → `.env` absent from the file list.
- Post-commit `git log --oneline` → single clean commit, working tree clean.

---

## 2026-08-16 — Phase 0: Formalize the log-then-commit journal protocol

**What happened**

- Added a `docs/DEV_JOURNAL.md` row to the key-files table and documentation map in
  `CLAUDE.md`, and to the doc index table in `README.md`.
- Added the explicit "Log-then-commit, strictly" protocol to `CLAUDE.md` → Working
  style: do the work → verify it → commit the work alone → write a journal entry →
  commit the journal entry separately. Work commits and journal commits are never
  bundled into one.
- Committed this as its own commit (`d4c12e6`), separate from creating the journal
  file itself and separate from the entry below.

**Why**

The point of this journal is to make "why did I do X" answerable months later without
reconstructing it from a diff — that only works if the discipline of writing it is
itself written down somewhere durable, not just agreed verbally. Putting it in
`CLAUDE.md` means every future session (a fresh Claude Code instance with no memory of
this conversation) picks up the same discipline automatically, since `CLAUDE.md` is
read at the start of every session.

**Decisions made**

- Journal entries are ordered newest-first, so opening the file mid-project shows the
  latest reasoning immediately (matches `CLAUDE.md`'s existing "Current status" section,
  which exists for the same fast-orientation reason). *(Superseded 2026-08-17 — see the
  final entry in this file: the project switched to oldest-first/chronological order.)*
- One entry generally corresponds to one work commit, cross-referenced by short hash,
  so the journal can be used to walk the commit history narratively.

**Verification**

- `git diff` reviewed line-by-line before staging — confirmed the addition was purely
  additive (15 insertions, 0 deletions across both files).
- `git status` after commit → working tree clean apart from the not-yet-committed
  journal file itself.

---

## 2026-08-17 — Phase 0: Env fixes and toolchain verification

**What happened**

- Renamed `SUPABASE_CONNECTION_STRING` → `DATABASE_URL` in `.env` to match the naming
  every doc (`DEPLOYMENT.md`, the Phase 2 ingestion prompts) actually expects. Also
  trimmed a trailing space that had snuck onto the end of `SUPABASE_URL`.
- Verified the Gemini key by calling Google's `generativelanguage.googleapis.com/v1beta/models`
  endpoint directly with it. Got back `HTTP 200` and a real model list including
  `gemini-2.5-flash` — so the unusual `AQ.`-prefixed format flagged yesterday was a
  false alarm; it's a valid key, just not the more common `AIzaSy...` shape. Confirmed
  by hitting the actual API rather than pattern-matching the string, which is the only
  way to really know a credential works.
- Checked the three remaining Phase 0 toolchain items from `BUILD_PLAN.md`:
  - **Python** — `python --version` → 3.12.10 (spec requires 3.11+, satisfied). Note:
    `python3` is not on PATH on this machine (Windows App Execution Alias stub only);
    use `python`, not `python3`, in any scripts or docs going forward.
  - **Node** — `node --version` → v22.15.0 (spec requires 18+, satisfied).
  - **uv** — not installed. Installed via Astral's official installer
    (`irm https://astral.sh/uv/install.ps1 | iex`), which placed `uv.exe` in
    `C:\Users\pandi\.local\bin` and added that directory to the persistent **User**
    `PATH` (verified via the Windows registry, not just the installer's own claim).
    Confirmed the binary itself works by invoking it with a full path
    (`uv 0.12.5`). Bare `uv` doesn't resolve *inside this same tool session* because
    that session's shell process started before the PATH update and Windows doesn't
    retroactively push registry PATH changes into already-running processes — this is
    expected and resolves itself the next time a terminal is opened fresh.

**Why**

`DATABASE_URL` naming matters now, before Phase 2, because it's exactly the kind of
mismatch that turns into a silent `None`/connection failure buried three layers into
ingestion code — cheaper to fix while it's one line in `.env` than to debug later
through a stack trace. Verifying the Gemini key against the real endpoint rather than
just eyeballing its shape is the same principle applied to credentials: a format
guess is not a verification.

**Decisions made**

- Standardized on `python` (not `python3`) as the interpreter command for this project
  on this machine, since that's what's actually on PATH.
- Phase 0's toolchain checklist is now fully satisfied — nothing blocks starting the
  P0.1 repository skeleton.

**Verification**

- `curl` against the Gemini `models` endpoint → `HTTP_STATUS:200`, valid JSON with
  `gemini-2.5-flash` present.
- `python --version` → `3.12.10`; `node --version` → `v22.15.0`.
- `uv.exe --version` via full path → `uv 0.12.5`; confirmed
  `[System.Environment]::GetEnvironmentVariable('Path','User')` includes
  `C:\Users\pandi\.local\bin`.
- `.env` re-read after edits to confirm `DATABASE_URL` present, no stray whitespace,
  and no other lines accidentally touched.

---

## 2026-08-17 — Phase 0: Virtual environment and LiveKit Agents dependencies

**What happened**

- Created `pyproject.toml` via `uv init --bare` — the `--bare` flag matters here: a
  normal `uv init` also scaffolds a sample `README.md`, a `main.py`, and re-runs `git
  init`, all of which this repo already has in a different shape (docs already
  written, `ARCHITECTURE.md` §5 specifies the real directory layout, git already
  initialized). `--bare` produces only the `pyproject.toml` itself: project name,
  description, `requires-python = ">=3.11"`.
- Ran `uv add livekit-agents livekit-plugins-deepgram livekit-plugins-google
  livekit-plugins-silero` — the exact package set named in
  `CLAUDE_CODE_PROMPTS.md` P0.2. This did three things in one command: created
  `.venv` (a project-local virtual environment, isolating these dependencies from
  anything else installed globally on the machine), resolved a full dependency graph
  (87 packages once transitive dependencies are included — e.g. `onnxruntime` for
  Silero's local VAD model, `google-genai` for the Gemini plugin, `opentelemetry-*`
  for the Agents framework's built-in tracing), and wrote `uv.lock`, which pins every
  resolved version exactly so a clean clone reproduces the identical environment
  rather than "whatever the latest compatible version happens to be today."
- Confirmed `.venv` is excluded from git (`.gitignore:14:.venv/`) and only
  `pyproject.toml` + `uv.lock` were staged — the dependency *declaration* and *lock*
  are committed; the actual installed environment is not and should never be (it's
  regenerated locally with `uv sync` or `uv add`, and committing it would bloat the
  repo with platform-specific binaries).
- Verified the installed versions directly rather than trusting the install log:
  `livekit-agents==1.6.10`, `livekit-plugins-deepgram==1.6.10`,
  `livekit-plugins-google==1.6.10`, `livekit-plugins-silero==1.6.10`.

**Why**

This was done deliberately *before* the full repository skeleton (P0.1), at the
owner's request. It's a reasonable reordering: nothing about scaffolding empty
`agent/`, `ingestion/`, `api/`, `web/` directories depends on dependencies being
installed, but confirming the LiveKit Agents SDK actually installs cleanly on this
machine, at this Python version, *does* matter before writing any structure around
it. It also sets up the very next step for free: `CLAUDE.md` rule #2 and
`CLAUDE_CODE_PROMPTS.md` P0.2 both insist that no pipeline code gets written from
memory — the installed package must be read directly to find the real API surface
(`AgentSession`, not the pre-1.0 `VoicePipelineAgent`). That reading step needs the
package installed first, which is now done.

**Decisions made**

- Used `uv init --bare` instead of hand-writing `pyproject.toml`, so the file's
  formatting and required fields match what `uv` itself expects rather than a
  guessed-at schema.
- Did not add a turn-detector plugin (`livekit-plugins-turn-detector`) or noise
  cancellation yet — staying scoped to exactly the P0.2 prompt's package list.
  SRS FR-2.2 requires semantic turn detection, so this is a flagged follow-up for
  Phase 1, not an oversight.

**Verification**

- `git status` after `uv add` → only `pyproject.toml` and `uv.lock` untracked;
  `.venv/` did not appear.
- `git check-ignore -v .venv` → matched `.gitignore:14:.venv/`.
- `uv pip list | grep livekit` → all four target packages present at matching
  versions across the board (`1.6.10`).
- Scanned `pyproject.toml` and `uv.lock` for secret-shaped strings before staging —
  none found (expected; lockfiles contain package hashes, not credentials).

---

## 2026-08-17 — Phase 0: Switch journal to chronological (oldest-first) order

**What happened**

- Reordered all four existing entries in this file from newest-first (LIFO) to
  oldest-first (FIFO) — the 2026-08-16 doc-review entry now leads, and each
  subsequent entry follows in the order it actually happened, ending with whichever
  entry was written most recently.
- Updated the "About this journal" section's convention line from "Newest entries are
  at the top" to "Entries are appended in chronological order — oldest at the top,
  most recent at the bottom. New entries always go at the **end** of the file."
- Added a superseded-note on the old "journal entries are ordered newest-first"
  decision recorded in the 2026-08-16 protocol entry, rather than silently deleting or
  rewriting it — the point of a journal is that past decisions stay visible even after
  they're reversed, including the reversal itself.
- Committed the reorder itself (`6ba9481`) as a work commit — pure reordering plus the
  one convention-line edit, no content changes to any existing entry — separate from
  this entry describing it.

**Why**

Newest-first was the original choice because it optimizes for "catch up fast
mid-project," mirroring `CLAUDE.md`'s "Current status" section. Oldest-first optimizes
for a different, and for this file's actual purpose, more important read: interview
prep means re-reading the whole thing as a narrative — how the project actually
unfolded, decision by decision — not scanning for the latest status. A journal read
top-to-bottom in the order things happened is easier to turn into a spoken answer
("first I did X, which led to Y, which is why Z") than one read bottom-to-top.

**Decisions made**

- Chronological order is now the permanent convention for this file: every future
  entry gets appended at the end, never inserted at the top.
- Chose to annotate the superseded decision inline rather than edit it away, to keep
  the journal itself honest about its own history — an editorial call consistent with
  the file's stated purpose.

**Verification**

- `git diff --stat` before staging → 148 insertions / 146 deletions, confirming the
  change was a reorder plus small header edits, not a content rewrite (the 2-line
  delta is the convention-note line and the superseded-note annotation).
- Re-read the full file top to bottom after the edit to confirm entries now run
  2026-08-16 (doc review) → 2026-08-16 (protocol) → 2026-08-17 (env fixes) →
  2026-08-17 (venv/deps), in the correct chronological order.
- Scanned for secret-shaped strings before staging — none found.

---

## 2026-08-17 — Phase 0: Repository skeleton (P0.1 completion)

**What happened**

- Created the full directory structure specified in `ARCHITECTURE.md` Sec5:
  `agent/` (`main.py`, `twin_agent.py`, `retrieval.py`, `citations.py`, `config.py`,
  `prompts/system_prompt.md`), `ingestion/` (`ingest.py`, `chunker.py`, `embedder.py`,
  `loaders/{pdf_loader,markdown_loader,github_mcp}.py`), `api/main.py`, plus
  placeholder `web/`, `corpus/`, and `tests/` directories.
- Every Python file got a module docstring describing its responsibility **and** the
  specific FR/ADR it maps to (e.g. `agent/citations.py`'s docstring cites ADR-005 and
  FR-4.1/4.2) — no logic yet, per `BUILD_PLAN.md` P0.1's explicit "do not implement
  logic yet."
- `web/`, `corpus/`, and `tests/` got a `README.md` instead of a Python docstring
  (they're not Python packages) explaining what arrives there and in which phase.
- Left `agent/prompts/system_prompt.md` genuinely empty (just an HTML comment
  placeholder) rather than pre-filling the grounding contract from
  `CITATION_SPEC.md` Sec5 — that's explicitly P3.2's job, not P0.1's, and writing it
  now would mean writing it twice (once now, once for real once `OWNER_NAME` and the
  actual voice are settled).
- Flagged, not decided: whether `corpus/` should be added to `.gitignore` once real
  documents (resume, personal context) land in it — noted in `corpus/README.md` as a
  pending decision rather than assumed either way.

**Why**

The skeleton's value isn't the empty files themselves — it's that every future
Claude Code session (or the owner, reading cold) can see the intended shape of the
system without re-deriving it from `ARCHITECTURE.md` prose each time, and the
docstrings double as a standing checklist of what each module still owes the spec.

**Decisions made**

- Added `__init__.py` to `agent/`, `ingestion/`, `ingestion/loaders/`, and `api/` even
  though `ARCHITECTURE.md`'s tree diagram doesn't show them explicitly — Python
  namespace packages work without them, but explicit `__init__.py` is what the
  LiveKit Agents CLI's own module-discovery code
  (`livekit/agents/cli/discover.py`) expects when walking parent directories looking
  for package boundaries (confirmed while researching P0.2 below).

**Verification**

- `find . -maxdepth 3` before and after, diffed by eye against the `ARCHITECTURE.md`
  Sec5 tree — exact match.
- Scanned every new file for secret-shaped strings before staging — none found
  (expected; these are docstring-only placeholders).
- `git status` after staging → exactly the 20 new files intended, nothing else.

---

## 2026-08-17 — Phase 0: Verified LiveKit Agents SDK surface (P0.2 completion)

**What happened**

- Read the actual installed `livekit-agents==1.6.10` source directly — not a
  tutorial, not memory — under `.venv/Lib/site-packages/livekit/`, and ran real
  `inspect.signature()` calls against the installed plugin classes to confirm
  constructor defaults, per `CLAUDE.md` rule #2 and `CLAUDE_CODE_PROMPTS.md` P0.2.
- Wrote `docs/SDK_NOTES.md` covering the four things P0.2 asks for: session/agent
  primitives, function tool definition, data channel publishing, and worker
  entrypoint registration.
- **The headline finding:** the entrypoint pattern has moved again since the
  `VoicePipelineAgent` → `AgentSession` change most "1.0" tutorials already know
  about. The classic `cli.run_app(WorkerOptions(entrypoint_fnc=...))` still runs, but
  its own docstring in the installed package calls it "the (deprecated) rich Python
  CLI [...] being phased out in favor of [...] `AgentServer`." The current pattern is
  `server = AgentServer()` plus a `@server.rtc_session(agent_name=...)` decorator
  around the entrypoint function, with the `AgentServer` instance stored in a
  module-level variable literally named `app`, `server`, or `agent` — the CLI's
  `discover.py` looks for exactly those three names, in that priority order, when
  resolving `python -m livekit.agents start agent/main.py`.
- Found that `RunContext` (the object passed into a `@function_tool`-decorated
  method) doesn't carry the room directly, but `get_job_context()` — a
  `contextvars.ContextVar` lookup — does, and works from *anywhere* inside a running
  job, including deep inside a tool call. This means `agent/citations.py` can call
  `get_job_context().room.local_participant.publish_data(...)` without `TwinAgent`
  needing to manually thread a `JobContext` through its constructor.
- Found and documented a real, concrete env-var mismatch before it became a Phase 1
  bug: `livekit-plugins-google`'s `LLM` class resolves its API key as
  `api_key if given else os.environ.get("GOOGLE_API_KEY")` — it reads
  `GOOGLE_API_KEY`, not `GEMINI_API_KEY`, which is what this project's `.env` and
  `DEPLOYMENT.md` actually use. Confirmed by reading
  `livekit/plugins/google/llm.py` line 196 directly, not by guessing. Documented the
  fix for Phase 1: pass `api_key=os.environ["GEMINI_API_KEY"]` explicitly in
  `agent/config.py` rather than introducing a second, duplicate env var.
- Also confirmed `silero.VAD` is instantiated via the classmethod `VAD.load(...)`,
  not `VAD()` directly — an easy one-line mistake to make from memory.
- Added `docs/SDK_NOTES.md` to `README.md`'s document index table (it was already
  referenced in `CLAUDE.md`'s documentation map from the original template, but
  missing from `README.md`'s table — the same category of gap the DEV_JOURNAL.md row
  had earlier).

**Why**

This is the single most repeated instruction across every doc in this project
(`CLAUDE.md` rule #2, `README.md`'s ground rules, `BUILD_PLAN.md` Phase 1, every
relevant prompt in `CLAUDE_CODE_PROMPTS.md`) for a concrete reason: the framework has
now changed its top-level entrypoint pattern *twice* in ways a plausible-sounding
tutorial from six months ago would get wrong, and the `GOOGLE_API_KEY` vs
`GEMINI_API_KEY` mismatch is exactly the kind of bug that would otherwise surface as
a confusing runtime error deep into Phase 1, several layers away from its actual
one-line cause. Reading the installed source first turns both into a documented fact
instead of a debugging session.

**Decisions made**

- `agent/main.py` will use the `AgentServer` + `@server.rtc_session` pattern, not
  `WorkerOptions` + `cli.run_app`, when Phase 1 writes real code — the deprecated
  path was ruled out now specifically so Phase 1 doesn't have to make this call under
  time pressure.
- `agent/config.py` will explicitly pass `api_key=` to `google.LLM(...)` from
  `GEMINI_API_KEY` rather than setting `GOOGLE_API_KEY` as a second copy of the same
  secret in the environment.

**Verification**

- Every claim in `docs/SDK_NOTES.md` traces to either a direct source-file read
  (with file path cited inline) or a real `inspect.signature()`/`isinstance` check
  run against the installed package in this machine's `.venv` — not to documentation
  site prose or training-data recall.
- Scanned `docs/SDK_NOTES.md` and the `README.md` diff for secret-shaped strings
  before staging — none found.
- `git status` after staging → exactly `docs/SDK_NOTES.md` (new) and `README.md`
  (modified), nothing else swept in.

---

## 2026-08-17 — Phase 0: Marked complete in CLAUDE.md status

**What happened**

- Checked off Phase 0 in `CLAUDE.md`'s "Current status" section and rewrote "Now
  working on" / "Blocked by" to point at Phase 1, carrying forward the two open
  follow-ups from `docs/SDK_NOTES.md` (the `GEMINI_API_KEY`/`GOOGLE_API_KEY` mismatch
  and the missing turn-detector plugin) so a fresh session doesn't have to re-read
  the full SDK notes just to know what's still open.

**Why**

`CLAUDE.md` explicitly says this section exists so "a new session gets oriented
fast" — leaving it stale after finishing a phase defeats that purpose the first time
someone (or a future Claude Code session with no memory of this conversation) opens
the file expecting it to be current.

**Decisions made**

- None beyond the status update itself.

**Verification**

- Scanned for secret-shaped strings before staging — none found.
- `git status` after staging → only `CLAUDE.md`.

---

## 2026-08-17 — Phase 1: Audio round-trip (live-verified)

**What happened**

Built and live-tested the first real pipeline code, following the plan in
`BUILD_PLAN.md` Phase 1 / `CLAUDE_CODE_PROMPTS.md` P1.1+P1.3 combined. Went through
plan mode first since this was the first non-trivial implementation step in the repo.

- **`agent/config.py`**: exposes `GEMINI_API_KEY` (re-passed explicitly to
  `google.LLM` since the plugin reads `GOOGLE_API_KEY` by default — the Phase 0
  finding) and `GEMINI_MODEL` with a default. Added an explicit
  `dotenv.load_dotenv()` call.
- **`agent/main.py`**: `AgentServer()` at module level, `@server.rtc_session()`
  decorating the entrypoint, `AgentSession` wired with `deepgram.STT()`,
  `google.LLM(...)`, `deepgram.TTS()`, `silero.VAD.load()`, and
  `livekit.agents.inference.TurnDetector()` for semantic turn detection (FR-2.2).
  Trivial, no-persona instructions — no retrieval, no owner name — per P1.1's
  explicit "a friendly assistant, no retrieval yet." Structured logging on
  `agent_state_changed`, `user_state_changed`, `user_input_transcribed`, and
  `conversation_item_added`. Greeting via `session.generate_reply(...)` on start,
  for FR-1.6.

**Three real bugs, caught by running the thing instead of trusting the plan**

The plan (written from `SDK_NOTES.md`'s Phase 0 research plus reasonable-sounding
assumptions) got three separate things wrong that only surfaced by actually running
the worker against LiveKit Cloud:

1. **`agent_name="voice-twin"` broke automatic dispatch.** Following the SDK's own
   docstring example too literally, the first version of `agent/main.py` passed
   `agent_name="voice-twin"` to `@server.rtc_session(...)`. Read closely, the SDK's
   own field docstring says a non-empty `agent_name` "enable[s] explicit dispatch...
   jobs will not be dispatched to rooms automatically" — the exact opposite of
   FR-1.4. Caught by reading that docstring *before* the first live test, not by
   debugging a mysteriously-idle worker. Fixed by dropping `agent_name` entirely
   (default `""`), confirmed by the "registered worker" log line switching from
   `"agent_name": "voice-twin"` to `"agent_name": ""`.
2. **`uv run` does not auto-load `.env`.** The Phase 1 plan explicitly claimed
   otherwise, reasoning from `uv run --help` showing `--env-file`/`--no-env-file`
   flags and assuming that meant env-file loading was on by default. It isn't —
   confirmed by `uv run python -c "import os; print('GEMINI_API_KEY' in os.environ)"`
   printing `False`. This is exactly the "should work" trap `CLAUDE.md` warns
   against: the flags' *existence* was real, the *inferred default behavior* was a
   guess, and the guess was wrong. Fixed with an explicit `python-dotenv` dependency
   and `load_dotenv()` in `agent/config.py`, which is also more portable than
   relying on `uv run`'s flags once this deploys somewhere that isn't `uv run`.
3. **`gemini-2.5-flash` (the plugin's own compiled-in default, and
   `DEPLOYMENT.md`'s original documented default) is dead.** First live LLM call
   returned `HTTP 404: "This model models/gemini-2.5-flash is no longer available to
   new users."` — despite the model still appearing in the `/models` listing
   endpoint, which is what Phase 0's verification had checked. Listing a model and
   being eligible to call it are different things. Tested candidates directly via
   `curl` against `generateContent` (not the listing endpoint) before touching code:
   `gemini-2.5-flash` and `gemini-2.5-flash-lite` both 404 the same way;
   `gemini-flash-latest` (a rolling alias Google maintains to its current
   recommended flash model) works, resolving to `gemini-3.7-flash` at time of
   writing. Switched the default in `agent/config.py`, `.env.example`, and
   `DEPLOYMENT.md` to the alias specifically so the *next* pinned-version retirement
   doesn't repeat this exact break.

A fourth thing was corrected before it became a bug: `agent/main.py`'s first draft
logged via `session.on("metrics_collected", ...)`, which live testing immediately
flagged with a runtime `DeprecationWarning` — *"metrics_collected is deprecated. Use
session_usage_updated for usage tracking and ChatMessage.metrics for per-turn
latency."* Rewrote the handler to listen on `conversation_item_added` and read
`ChatMessage.metrics` instead, which turned out to be a strictly better fit anyway:
it's per-conversation-turn rather than per-pipeline-stage-event, and its
`e2e_latency` field is exactly NFR-1.1's "end-of-utterance to first audio byte"
definition, pre-computed.

**Live verification (via LiveKit Cloud's built-in Console, not the standalone
Agents Playground — that tool now redirects into the Cloud dashboard's own "Agent
Console")**

All `BUILD_PLAN.md` Phase 1 exit criteria confirmed on a real session
(room `console-ecabc7a7`, 44s duration):

- Worker registered and logged `"registered worker"` with `agent_name: ""`.
- Browser joined, mic permission granted, worker dispatched automatically — no
  manual step.
- Transcripts were accurate: `'Hi.'`, `'You hear my voice?'`, `'Introduce
  yourself.'`, `'I said stop it.'` all matched what was actually said.
- Bot replied in audible speech, confirmed by ear ("connected and it replied,
  sounds decent").
- **Barge-in worked**: `user_state` flipped to `speaking` at `13:20:20.285` while
  the agent was mid-reply; `agent_state` flipped from `speaking` to `listening` at
  `13:20:20.740` — about 455ms later. That's state-transition-log granularity, not
  an instrumented audio-cutoff measurement, and it's somewhat over FR-2.4's 300ms
  target — worth a tighter measurement later, but functionally the agent did stop
  talking when talked over, which is what Phase 1's exit criterion actually asks for.

**Honest latency finding — the one thing not to gloss over**

The Console's own session summary reported **average LLM time-to-first-token:
2,479ms** and **average end-to-end latency: 3,286ms** across the session. My own
per-turn logs from `ChatMessage.metrics` back this up and show the spread: one reply
came back in a very reasonable `llm_ttft=0.97s` / `e2e_latency=1.77s`, another spiked
to `llm_ttft=7.01s` / `e2e_latency=7.84s` for no visible reason in the logs (no
retry, no error — just a slow Gemini response). Both numbers are well above NFR-1.4's
<500ms LLM-first-token target and NFR-1.1's <1.5s median end-to-end target.

Subjectively, the owner described it as "not slow and not so fast, replies in a sec
or two" — which doesn't match the measured 2.5–3.3s averages. That gap between felt
latency and measured latency is worth remembering for the write-up: perceived
latency and instrumented latency are genuinely different things, and only one of
them is trustworthy evidence. This isn't a Phase 1 blocker — `BUILD_PLAN.md`'s exit
bar for this phase is the much softer "feels under ~2s," and formal NFR-1 tuning is
explicitly later work (Phase 3 once the real system prompt exists, hardened in
Phase 6) — but it's now a concrete, numbers-backed item to revisit rather than a
vague "latency might be an issue."

**Decisions made**

- `agent/main.py` uses no `agent_name`, keeping automatic dispatch (FR-1.4) as the
  permanent choice, not just a Phase 1 default.
- `GEMINI_MODEL` defaults to the `gemini-flash-latest` alias rather than a pinned
  version number, traded for a small amount of version-drift risk in exchange for
  not repeating this exact failure mode.
- Latency tuning is explicitly deferred, not ignored — logged here with real
  numbers specifically so it isn't lost before Phase 3/6.

**Verification**

- Live session against real LiveKit Cloud infrastructure (not a mock/simulation),
  observed via both the Console's own UI and this project's own structured worker
  logs simultaneously, cross-checked against each other.
- `uv run python -c "import agent.main"` sanity-checked after every code change,
  before spending time on a live run.
- Direct `curl` calls against Google's `generateContent` endpoint verified model
  availability before changing code, rather than inferring it from the `/models`
  listing or from the plugin's error message alone.
- Scanned every changed file for secret-shaped strings before staging — none found.
- `git status` after staging → exactly the 7 files in commit `3389d18`, nothing
  extra swept in.

---

## 2026-08-17 — Phase 1: Marked complete in CLAUDE.md status

**What happened**

- Checked off Phase 1 in `CLAUDE.md` and rewrote "Now working on" to point at
  Phase 2, carrying forward the two open, non-blocking items from the Phase 1 entry
  above: the measured LLM latency (2.5s average TTFT, one 7s spike) and the
  approximate barge-in timing (~455ms by log granularity, not a precise
  instrumented cutoff) — both real numbers worth revisiting once Phase 3's real
  system prompt exists, not vague TODOs.

**Why**

Same reasoning as the Phase 0 equivalent entry: `CLAUDE.md`'s status section exists
so a session with no memory of this conversation can orient immediately, and that
only works if it's kept current the moment a phase actually closes.

**Decisions made**

- None beyond the status update itself.

**Verification**

- Scanned for secret-shaped strings before staging — none found.
- `git status` after staging → only `CLAUDE.md`.

---

## 2026-08-18 — Phase 2: Corpus content — context.md interview, identity config, privacy decision

**What happened**

- Found `corpus/AI Engineer Resume.pdf` already sitting in the repo, untracked, from
  before this session — read it directly (not asked-about-secondhand) to ground
  everything that followed in real content: four projects (JobHunt AI, the
  Self-Reflective RAG platform, a loan risk-scoring system, and the Project Nexus
  homelab), a freelance role, and CS undergrad education.
- Ran the `DATA_INGESTION.md` §2 interview conversationally rather than handing over a
  blank template — asked the seven questions the doc lists (current work, why this
  field, strongest project and what was actually hard about it, depth map, what's
  being looked for, a real failure, how learning happens) one round, got real answers.
- For the "strongest project" answer, the owner pointed at a specific GitHub repo
  (`Heuristic-Self-Reflective-RAG`) rather than re-describing it from memory. Fetched
  the actual README via `WebFetch` against the raw GitHub URL (`gh` CLI isn't
  installed on this machine, confirmed by `command not found`, so fell back to the
  documented alternative) instead of taking the resume's one-line project summary at
  face value. That surfaced real substance the resume didn't carry: a heuristic risk
  score built from mean similarity + score spread + proportional penalties, a
  configurable 0.70 threshold, an autonomous top_k-expansion retry, and — the genuinely
  interesting part — a benchmark finding that expanding context for out-of-domain
  queries *increases* hallucination risk rather than helping, which inverted the
  owner's own initial intuition. That level of detail is exactly what `context.md` is
  supposed to capture and a resume bullet can't.
- Wrote `corpus/context.md` (1,377 words, within the 1,000–2,000 target) with one `##`
  section per interview topic, so the ingestion chunker (once built) splits on real
  topic boundaries rather than arbitrary token windows, per `DATA_INGESTION.md` §3.
  First person, conversational, written to be spoken by TTS rather than read as
  prose — matches `CLAUDE.md` rule #7 even though this file feeds retrieval text, not
  direct bot output, on the theory that grounding text closer to speakable phrasing
  reduces how much the LLM has to transform it.
- Set `OWNER_NAME=Pandidharan Gopiraj` and added `RETRIEVAL_THRESHOLD=0.35`,
  `RETRIEVAL_TOP_K=4`, `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5` to `.env` — these were
  documented in `.env.example` and referenced in `agent/config.py`'s docstring since
  Phase 0/1 but never actually set, since nothing read them yet. `GITHUB_USERNAME` was
  already correctly set to `Pandidharan22` from an earlier session.
- **Privacy decision, previously left open:** `corpus/README.md` had flagged since
  Phase 0 that the directory should probably be gitignored once real documents with
  personal contact info landed in it, without deciding. Surfaced it explicitly rather
  than assuming either way, since it's a hard-to-reverse call once something is pushed
  to public git history. Asked; the owner chose to gitignore `corpus/*` (except
  `README.md`) rather than commit source documents or scrub them — the resume and
  `context.md` carry a phone number and email. Source files stay local-only, get
  ingested into Supabase, and the deployed bot can still cite them by filename; they
  just never enter git history. Updated `.gitignore` and rewrote `corpus/README.md`'s
  pending-note into a resolved decision record.

**Why**

The interview-then-write approach (rather than asking for a document dump) exists
because `context.md`'s entire value proposition, per `DATA_INGESTION.md`, is content a
resume has no room for — the "what was actually hard" and "what did you learn from
failing" answers only come out through conversation, not document extraction. Fetching
the real README instead of trusting the resume's one-liner mattered for the same
reason CLAUDE.md rule #2 insists on reading the installed SDK instead of reproducing a
tutorial from memory: a plausible-sounding secondhand summary and a verified primary
source are not the same thing, and the gap between them is exactly where a citation-
grounded bot would eventually get caught fabricating or flattening detail.

The privacy call was worth pausing for rather than defaulting silently, because
`.env`-style secrets aren't the only thing rule #1 should cover in spirit — a phone
number in permanent public git history is a different, less reversible kind of
exposure than the same number being spoken by the bot to one visitor at a time, even
though the underlying fact is already going to be retrievable either way once the app
is live.

**Decisions made**

- `corpus/context.md` is the canonical handwritten grounding document going forward;
  future updates to it happen by editing the file directly, not by re-running the
  interview from scratch.
- `corpus/*` is gitignored except `README.md`. Anyone cloning this repo must supply
  their own corpus files locally before ingestion will produce anything — documented
  in the rewritten `corpus/README.md`, not left implicit.
- `OWNER_NAME`, `RETRIEVAL_THRESHOLD`, `RETRIEVAL_TOP_K`, and `EMBEDDING_MODEL` are now
  real, set values, not placeholders — `RETRIEVAL_THRESHOLD=0.35` and
  `RETRIEVAL_TOP_K=4` are the `.env.example` defaults, carried forward unchanged;
  actual threshold tuning against the spot-check queries is still open work for later
  in Phase 2/3, not decided here.

**Verification**

- `wc -w corpus/context.md` → 1,377, inside the `DATA_INGESTION.md` §2 target range.
- `git check-ignore -v` against both corpus source files and `.env` after the
  `.gitignore` edit → all three correctly matched and excluded.
- `git status --short` after the edit → only `.gitignore` and `corpus/README.md`
  modified; the resume PDF and `context.md` correctly absent from the list.
- `git diff` on the two staged files, grepped for secret-shaped patterns
  (`AIza`, `github_pat_`, JWT `eyJ`, PEM headers, `postgresql://`, `api_key`) — zero
  matches.
- Committed the gitignore/README privacy fix (`61b6ecb`) as its own work commit,
  separate from this journal entry, per the log-then-commit protocol.

---

## 2026-08-19 — Phase 2: Planning the pipeline; GitHub REST vs. MCP client decision

**What happened**

- Before writing any ingestion code, went through plan mode to design the full
  loaders → chunker → embedder → Supabase pipeline, per `CLAUDE.md`'s "plan before
  implementing anything non-trivial."
- Researched, rather than assumed, two open implementation questions live during
  planning: (1) how Supabase's pgvector similarity search is actually wired up from
  Python — confirmed the standard pattern is a Postgres function (`match_documents`/
  `match_chunks` style) called via `supabase-py`'s `.rpc()`, since PostgREST can't
  execute the `<=>` vector-distance operator directly; (2) how the official GitHub MCP
  server actually works end to end, since `DATA_INGESTION.md` names it specifically
  rather than "call the GitHub API."
- **The GitHub MCP finding, explained to the owner before deciding:** the official
  server (`github/github-mcp-server`) isn't a different data source — it's a separate
  process (Docker container or binary) that itself calls the same GitHub REST/GraphQL
  API, and exposes that as MCP tools over a stdio JSON-RPC protocol. Using it from
  `ingest.py` means spawning that process as a subprocess and speaking MCP as a
  client (Python `mcp` SDK), rather than one HTTP call. Same underlying data either
  way; the only thing MCP adds here is a second process, a new dependency, and a
  Docker requirement that has to be satisfied wherever ingestion runs — including the
  GitHub Actions cron in Phase 5.
- Walked the owner through the actual mechanics of both paths (not just a summary
  trade-off) before asking them to choose, since "which is simpler" isn't answerable
  without seeing what each one actually requires. **Decision: plain REST API** (PAT +
  `httpx`, direct to `api.github.com`) — identical data, one fewer moving part, no
  Docker dependency to keep alive through deployment and the ingestion cron.
- This is a real deviation from `ARCHITECTURE.md` ADR-002/ADR-003's literal "MCP
  client" language, so the plan calls for **amending both ADRs with a note**, not
  quietly implementing something different from what the docs claim — same principle
  the journal itself already follows (annotate reversed decisions, don't erase them).
  `ingestion/loaders/github_mcp.py` will be renamed to `github_loader.py` so the
  filename stops implying a protocol the code doesn't use.
- Wrote the approved plan to
  `C:\Users\pandi\.claude\plans\polished-dazzling-sunrise.md`: Supabase schema
  (`chunks` table + `match_chunks` RPC, applied via direct `psycopg` connection since
  DDL can't go through PostgREST), three loaders (PDF tuned to this resume's actual
  section structure, markdown split on `##`, GitHub via REST), a chunker enforcing the
  size floor/ceiling and contextual prefixing, a local `bge-small-en-v1.5` embedder,
  an idempotent upsert orchestrator, and a validation script with 5 spot-check queries
  written against the real corpus content that now exists.
- Created 11 tracked tasks (`TaskCreate`) mirroring the plan's build order, to work
  through one at a time with the log-then-commit protocol applied per meaningful step
  rather than one large end-of-phase commit.

**Why**

Planning mattered here specifically because the GitHub ingestion question had a real
architectural fork with asymmetric stakes — not "which is cleaner" but "one of these
introduces an infrastructure dependency that could quietly break the Phase 5 cold-start
test." `BUILD_PLAN.md`'s own Phase 5 section calls the cold-start test "not optional,"
which made the Docker-availability question concrete rather than theoretical. Explaining
the mechanics before asking for a decision, instead of presenting a pre-digested
recommendation, matched what the owner actually asked for when the first attempt at
this question got rejected mid-plan.

**Decisions made**

- GitHub content enters via plain REST + PAT, permanently — not deferred, not "MCP
  later." Documented as an amendment to ADR-002/ADR-003, not a silent contradiction of
  them.
- `ingestion/loaders/github_mcp.py` → `ingestion/loaders/github_loader.py`.
- Supabase schema changes go through a direct `psycopg`/`DATABASE_URL` connection,
  never through `supabase-py`'s table/rpc client, since the latter can't run DDL.
- Chunk size heuristics use `tiktoken`'s `cl100k_base` encoding as a consistent
  yardstick — explicitly not claimed to match Gemini's real tokenizer, just needs
  internal consistency for the floor/ceiling rule.

**Verification**

- N/A for this entry — planning only, no code changed. Verification lands per-step as
  each task in the plan is implemented and committed.

---

## 2026-08-19 — Phase 2: Ingestion dependencies

**What happened**

- `uv add "psycopg[binary]" pypdf httpx tiktoken sentence-transformers supabase` — the
  six packages the approved plan calls for. Resolved 147 packages total; the heavy
  ones are transitive, not direct — `torch` (116MB), `scipy`, `transformers`, and
  `scikit-learn` all come in underneath `sentence-transformers`, which needs a real
  PyTorch backend to run the `bge-small-en-v1.5` model locally.
- `httpx` didn't need adding explicitly in the end — `uv add` resolved it in as a
  transitive dependency of `supabase`'s `postgrest`/`storage3` clients already, at
  `0.28.1`, which satisfies what the GitHub loader needs. Listed it directly in
  `pyproject.toml` anyway (`httpx>=0.28.1`) rather than relying on it staying
  transitively present — the GitHub loader's own dependency on it should be explicit
  in the manifest, not implicit through an unrelated package's requirements.
- Verified all six land at usable versions via `uv pip list`, rather than trusting the
  install log alone: `psycopg==3.3.4`, `pypdf==6.16.1`, `httpx==0.28.1`,
  `tiktoken==0.14.0`, `sentence-transformers==6.0.0`, `supabase==2.31.0`.

**Why**

Same "verify the install, don't trust the log" habit as Phase 0's LiveKit dependency
step — `uv add`'s own summary output only shows what changed in the resolution, not a
clean confirmation that each named package is actually importable at the version
expected.

**Decisions made**

- None beyond the dependency versions themselves, which are pinned by `uv.lock` as of
  this commit.

**Verification**

- `uv pip list | grep -iE` for all six target packages → all present, versions
  recorded above.
- `git diff pyproject.toml` reviewed line-by-line before staging — six additive
  dependency lines, nothing else touched.
- Scanned the diff for secret-shaped strings before staging — `uv.lock` only ever
  contains package hashes, not credentials; confirmed none found.
- `git status --short` after staging → only `pyproject.toml` and `uv.lock`.
- Committed as `ee315e6`, separate from this journal entry.

---

## 2026-08-19 — Phase 2: Supabase schema — chunks table and match_chunks RPC

**What happened**

- Wrote `ingestion/schema.sql`: enables the `vector` extension, creates the `chunks`
  table with all the fields `DATA_INGESTION.md` §4 requires (`source`, `source_type`,
  `section`, `text`, `source_url`, `content_hash` with a unique constraint,
  `embedding vector(384)`, `ingested_at`), an HNSW index on the embedding column for
  fast approximate cosine search, and a `match_chunks` SQL function.
- The function exists because PostgREST — the REST layer `supabase-py`'s table/rpc
  client actually talks to — has no way to evaluate pgvector's `<=>` distance operator
  directly through a normal table query. Wrapping the similarity search in a Postgres
  function and calling it via `.rpc("match_chunks", {...})` is the documented pattern
  (confirmed against Supabase's own docs during planning, not assumed). The function
  takes a query embedding, a similarity threshold, and a result count, and returns
  chunks scoring above threshold ordered by distance — this *is* FR-3.3's threshold
  gate, implemented at the database layer rather than filtered in Python after the
  fact, so a below-threshold chunk never even leaves Postgres.
- Added `setup_db()` to `ingestion/ingest.py` — reads `schema.sql` and executes it
  over a direct `psycopg` connection using `DATABASE_URL`, since DDL (extensions,
  tables, functions) has to go through a real Postgres connection, not the REST API.
  Every statement in the file is `if not exists` / `or replace`, so re-running is
  always safe.
- **Ran it for real against the live Supabase project**, twice — not described, not
  assumed to work. First run applied the schema; then queried
  `pg_extension`/`information_schema.columns`/`pg_proc`/`pg_indexes` directly to
  confirm the extension, all nine expected columns, the function, and both indexes
  (primary key, unique `content_hash`, and the HNSW index) actually exist in the
  database — not just that the script exited without error. Second run confirmed
  idempotency: no errors, nothing duplicated, matching FR-6.4's requirement one layer
  down from where it usually gets tested (schema-level, not row-level, but the same
  principle).

**Why**

`CLAUDE.md`'s "run things, don't say this should work" rule applies as much to
database migrations as to application code — a `CREATE TABLE IF NOT EXISTS` that
silently no-ops because of a typo in a column name would still print success and
would still be wrong. Querying Postgres's own system catalogs after running the
script is what actually closes that gap.

**Decisions made**

- Schema application lives in `ingest.py` as `setup_db()`, callable both from the
  module's own `__main__` block (for standalone runs, useful during this kind of
  verification) and, later, from the full orchestrator before loaders run.
- No separate migrations tool (Supabase CLI, Alembic) introduced for a single
  idempotent schema file — proportionate to the project's size; would reconsider if
  the schema needed versioned migrations later.

**Verification**

- `uv run python -m ingestion.ingest` → `Schema applied.`, run twice, both clean.
- Direct psycopg queries against `pg_extension`, `information_schema.columns`,
  `pg_proc`, and `pg_indexes` after the first run — all expected objects present and
  correctly shaped, checked against the live database rather than trusted from the
  script's own exit status.
- Scanned `ingest.py` and `schema.sql` diffs for secret-shaped strings before staging
  — none found (the file reads `DATABASE_URL` from the environment, never contains
  it).
- `git status --short` after staging → only the two intended files.
- Committed as `7bae34c`, separate from this journal entry.

---

## 2026-08-19 — Phase 2: PDF loader — resume, tuned to its real extracted structure

**What happened**

- Before writing any splitting logic, ran `pypdf`'s actual `extract_text()` against
  the real resume and printed the raw output, rather than assuming a PDF text
  extractor preserves the visual layout. It doesn't, in two specific ways: (1) some
  spaces around `:`/`&`/`/` characters vanish — `"AI/ML&GenAI:Python, ..."` instead of
  `"AI / ML & GenAI: Python, ..."` — apparently because pypdf's whitespace-insertion
  heuristic depends on inter-glyph gap size, and a few gaps in this PDF's layout fall
  under whatever threshold it uses; (2) a project's title and its right-aligned
  category tag ("Agentic AI / Open Source") share one visual row in the PDF, so they
  extract as a single run-together line since pypdf reads left-to-right per line, not
  per visual column.
- Built `ingestion/loaders/pdf_loader.py` around the resume's *actual* six section
  headers (confirmed as literal standalone lines in the extracted text: Objective,
  Technical Skills, Projects, Experience / Freelance, Core Engineering Strengths,
  Education) rather than guessing at a generic resume schema. Technical Skills splits
  per category — including correctly handling that the first category's item list
  wraps across two PDF lines while the other four don't, by treating any line
  containing `:` as a new category rather than assuming one line per category.
  Projects splits into one chunk per entry by matching each of the four known
  title-prefixes at the start of a line (the run-together tag text after the prefix is
  discarded and replaced with a known-clean category tag, rather than trying to
  generically parse it back apart). Education pairs each bullet line with its
  following description line.
- Ran the loader against the real file and printed every resulting chunk — this
  surfaced two chunks that hadn't just lost a few spaces but had lost *all* of them:
  `"End-to-endMLsystemforloandefaultpredictionwithFastAPIbackend..."` (the loan project
  description) and `"Engineeredaproduction-gradeself-hostedhomelabcombining..."` (the
  homelab project description) — both extracted as one unbroken run with zero
  whitespace at all, a more severe version of the same pypdf quirk. Fixed both with
  targeted, verified string replacements rather than a generic regex, for the same
  reason the rest of the cleanup is targeted: a blanket "insert a space at every
  lowercase→uppercase boundary" rule would just as happily mangle correct terms
  elsewhere in the document (`GitHub` → `Git Hub`, `NumPy` → `Num Py`), trading one
  category of error for a different one.
- One thing that looked like a bug and wasn't: printing a chunk's `section` field
  showed a `�` character in place of the em-dash used in headings like `"Projects —
  Project Nexus"`. Checked with `ord()` directly on the actual string content rather
  than trusting what printed — confirmed the real character is U+2014 (em dash),
  correctly stored; the `�` is this Windows terminal's codepage failing to render it,
  not data corruption. Worth noting because it's exactly the kind of thing that's easy
  to "fix" incorrectly by mangling correct data to satisfy a terminal that's actually
  the thing at fault.
- Result: 15 clean chunks from one resume (1 contact block, 1 objective, 5 technical-
  skill categories, 4 projects, 1 experience entry, 1 core-strengths block, 2 education
  entries), all read as normal prose when printed.
- Added `ingestion/types.py` with a shared `RawSection` `NamedTuple` — the loader
  output shape (`source`, `source_type`, `section`, `text`, optional `source_url`) —
  so the markdown and GitHub loaders (next) and the chunker all agree on one contract
  instead of three ad hoc tuples.

**Why**

This is the same "verify, don't guess" discipline as `CLAUDE.md` rule #2, applied to a
library's actual output instead of an SDK's actual API — assuming a PDF extractor
preserves spacing would have shipped a loader that silently produced garbled citation
text on two of four projects, the kind of bug that's invisible until someone actually
reads a card in the UI. Printing every real chunk before moving on, rather than trusting
that the section-splitting logic "should" work, is what caught it.

**Decisions made**

- The PDF loader is explicitly scoped to this one resume's real structure, documented
  as such in its own module docstring — not a general-purpose resume parser. A
  differently formatted resume would need the section/project tables in this file
  adjusted.
- Text cleanup uses a curated list of verified exact-string replacements plus a small
  number of safe generic regexes (space-after-colon, space-after-comma), not a broad
  heuristic regex — chosen specifically to avoid trading known garbling for new,
  different garbling of already-correct terms.

**Verification**

- Ran `pdf_loader.load()` against the real `corpus/AI Engineer Resume.pdf` and printed
  every one of the 15 resulting chunks in full — read each one for readability, not
  just checked chunk count.
- Checked the em-dash question with `ord()` against the real string content before
  concluding it was a display artifact rather than a data bug.
- Scanned the diff for secret-shaped strings before staging — none found (this file
  only ever touches resume prose, no credentials).
- `git status --short` after staging → only the two intended new/changed files.
- Committed as `160db26`, separate from this journal entry.

---

## 2026-08-19 — Phase 2: Markdown loader for context.md

**What happened**

- Built `ingestion/loaders/markdown_loader.py`: split `context.md` on `##` headers via
  regex, yielding one `RawSection` per topic block. Deliberately drops the file's `#`
  title and its one-paragraph preamble ("This file exists to give a conversational AI
  the answers a resume has no room for...") rather than treating it as a chunk — it's
  commentary about the document itself, not something a visitor would ask the bot
  about, and embedding it risked it surfacing as a retrieved "answer" to some
  unrelated query.
  a `load_corpus_markdown()` wrapper walks `corpus/**/*.md` and explicitly skips
  `README.md` by name, since that file documents the directory, not the owner.
- Ran it against the real `context.md` and printed every resulting chunk with its word
  count: all 7 interview sections came back intact and correctly bounded, from 96
  words ("What I'm looking for") to 449 words (the RAG project section) — the larger
  one is over `DATA_INGESTION.md` §3's ~500-token ceiling once actually tokenized, but
  splitting oversized sections further is explicitly the chunker's job, not the
  loader's, so left as-is here by design.

**Why**

Markdown has none of the PDF loader's whitespace-collapse problems — the format
already preserves structure — so this loader is a fraction of the size of the PDF one
and didn't need the same investigative pass. The one real design decision was what
*not* to chunk (the file's own self-description), which matters for the same reason
`DATA_INGESTION.md` §3 cares about clean citation units generally: a chunk that answers
"what is this document" rather than "what is true about the owner" is noise a retrieval
threshold can't distinguish from a real answer.

**Decisions made**

- Loaders stay dumb about size limits — `markdown_loader.py` yields raw topic blocks
  regardless of length; `chunker.py` (next) owns the floor/ceiling enforcement for
  every source type uniformly, so that rule lives in exactly one place.

**Verification**

- Ran `load_corpus_markdown()` against the real `corpus/` directory — confirmed 7
  chunks from `context.md`, zero from `README.md`, and read each chunk's opening text
  to confirm section boundaries landed correctly.
- Scanned the diff for secret-shaped strings before staging — none found.
- `git status --short` after staging → only the one intended file.
- Committed as `af8358b`, separate from this journal entry.

---

## 2026-08-19 — Phase 2: GitHub loader (REST) — and a real curation call

**What happened**

- Verified the real API surface before writing anything: called
  `GET /users/{username}/repos` directly with the PAT to see actual shape/fields
  (`fork`, `archived`, `language`, `description`, `topics`), and confirmed
  `GET /repos/{owner}/{repo}/readme` with `Accept: application/vnd.github.raw`
  returns raw markdown text directly (no base64 decoding needed) and 404s cleanly
  for repos with no README — rather than assuming either shape from memory.
- Built `ingestion/loaders/github_loader.py`: lists repos, filters out forks and
  archived repos, fetches each README, strips badge lines (regex against the
  `[![...)](...)]  `/`![...](...)`  markdown-image shapes) and markdown horizontal
  rules, skips install/license/contributing/table-of-contents sections by header
  match, and splits the rest on `#`/`##` headers — same shape as the markdown
  loader, plus per-repo metadata (description, language, topics) folded into the
  first "Overview" chunk, and every chunk carries the repo's real `html_url` as
  `source_url` (the one loader where that field isn't null).
- Renamed the file from the skeleton's `github_mcp.py` and updated
  `loaders/__init__.py`'s docstring, closing out the naming half of the REST-over-MCP
  decision from the planning entry above.
- **Ran it against the real account with no curation filter first**, deliberately,
  to see actual scale before assuming: 212 chunks across 22 non-fork repos. Most of
  that volume was coursework/practice repos — `Movie-App`, `Pneumonia-Prediction-
  using-Convolutional-Neural-Networks`, `Named-Entity-Recognition`, and similar —
  that neither the resume nor `context.md` ever mentions. Combined with the 22
  chunks already produced by the resume and `context.md` loaders, that's 234+
  chunks against `BUILD_PLAN.md`'s 40–150 healthy-range exit criterion, and squarely
  the failure mode `DATA_INGESTION.md` §7 warns about by name: "a bot that cites
  `test-repo-3` looks careless."
- Surfaced this to the owner rather than deciding unilaterally which projects
  represent them professionally — that's a real identity/narrative call, not a
  technical one. Proposed a curated list matching what the resume and interview
  already reference (the four resume projects, the Mockbuilder failure story, and
  this project itself); owner approved it as proposed. Added `CURATED_REPOS` as an
  explicit, hand-maintained set in the loader — documented in its own comment as
  intentionally not auto-growing when new repos get created, so scope stays a
  deliberate choice each time rather than silent drift.
- Re-ran with the curation filter applied: **36 chunks across the 6 intended repos**,
  confirmed by grouping the real output by repo and printing every section header
  and word count.
- One more real bug caught by reading actual output rather than trusting the badge
  regex worked: the RAG repo's stripped README left a dangling `---` markdown
  horizontal rule at the end of its first chunk. Added an `_HR_LINE` filter
  alongside the badge filter once spotted, then re-verified the specific chunk text
  directly.
- Noted, not fixed: printing chunk section headers containing real emoji (`🚀`,
  `🔧`) crashes on `print()` in this Windows terminal (`cp1252` can't encode them) —
  confirmed via `.encode('ascii', 'replace')` that this is a terminal display
  limitation, not corrupted data; the actual stored strings are correct UTF-8 and
  will render fine wherever the citation UI actually runs.

**Why**

Curation mattered here for exactly the reason `DATA_INGESTION.md` names: retrieval
quality is capped by corpus quality, and a corpus padded with irrelevant coursework
repos doesn't just risk citing something embarrassing on an unlucky query — it also
dilutes what a broad question like "what have you built?" surfaces in the top-k
results. Asking rather than picking a heuristic (like "has a description set")
mattered because that heuristic turned out not to even correlate with what actually
matters — the flagship RAG repo has no `description` field set at all, so a
field-based filter would have silently dropped exactly the project the owner cares
most about while keeping lower-value ones that happen to have a description.

**Decisions made**

- GitHub ingestion is curated by an explicit allow-list, not "all non-fork repos" —
  permanently, not just for this run. Growing the list is a deliberate edit to
  `CURATED_REPOS`, not automatic.
- Boilerplate stripping now covers both badge images and horizontal rules; if a
  future repo's README reveals another boilerplate shape, the same "strip a
  specific verified pattern" approach applies rather than a broad catch-all.

**Verification**

- Ran the loader against the real GitHub API twice: once uncurated (212 chunks, used
  to make the curation decision concrete rather than theoretical) and once after
  adding `CURATED_REPOS` (36 chunks, matching the approved 6-repo list exactly).
- Printed every chunk's section header, word count, and `source_url` per repo and
  read them for coherence.
- Directly inspected the badge-stripped and hr-stripped text of the RAG repo's first
  chunk to confirm the cleanup actually worked on real content, not just that the
  regex compiled.
- Scanned the diff for secret-shaped strings before staging — none found (the loader
  reads `GITHUB_TOKEN` from the environment, never contains one).
- `git status --short` after staging → the rename (delete + new file) and the one
  `__init__.py` docstring edit, nothing else.
- Committed as `8a0ceff`, separate from this journal entry.

---

## 2026-08-19 — Phase 2: Chunker — and a real content-loss bug caught by running it

**What happened**

- Built `ingestion/chunker.py`: takes every loader's `RawSection` output and
  finalizes it into `ChunkRecord`s. Uses `tiktoken`'s `cl100k_base` encoding as a
  consistent size yardstick (not claimed to match Gemini's real tokenizer, just
  needs internal consistency), discards anything under the 40-token floor,
  and — for anything over the 500-token ceiling — splits on paragraph breaks
  first, falling back to sentence boundaries if a section has no paragraph
  structure (true for GitHub/markdown content, which keeps its real `\n\n`
  breaks; not true for PDF-derived chunks, which the loader already flattens to
  one line, but none of those approach the ceiling anyway). A split-off remainder
  that itself lands under the floor gets merged back into the previous piece
  rather than silently dropped. Builds the `[Source: X | Section: Y]` prefixed
  `embed_text` for the embedder while keeping `text` clean for citation display,
  and computes `content_hash` from source+section+text for the idempotent upsert.
  Added `ChunkRecord` to `types.py` alongside `RawSection`.
- **Ran the full three-loader → chunker pipeline against real data** before
  considering this done — not each piece in isolation. First result: 58 raw
  sections in, only 50 chunk records out. Printed every resume chunk with its
  token count to see exactly what the floor was discarding, rather than assuming
  the 8-chunk drop was all correctly-filtered noise.
- **It wasn't.** Four of five Technical Skills categories and both Education
  entries got silently discarded — each individually landed under the 40-token
  floor (a bare line like `"Frontend: React.js, Three.js, Tailwind CSS, Framer
  Motion, Streamlit"` is genuinely short, but it's real, legitimate, factual
  content, not noise). That's a real retrieval-quality bug: a visitor asking "do
  you know MongoDB?" or "what's your CGPA?" would have hit `no_match` and gotten
  a refusal, even though the answer was sitting right there in the source PDF —
  exactly the failure mode `DATA_INGESTION.md`'s validation step (§9) exists to
  catch before it reaches a voice interface.
- Traced the actual cause: not a chunker bug, a loader-scoping bug from the
  earlier PDF loader step. `DATA_INGESTION.md`'s own chunk-boundary table
  describes the resume's Technical Skills unit as "one skills block" —
  *singular* — but the PDF loader had split it into five, one per category,
  which was already off-spec before the floor ever touched it. Fixed at the
  source rather than papering over it in the chunker: `_split_technical_skills`
  now returns one combined chunk for the whole section (151 tokens, comfortably
  inside DATA_INGESTION's 100–300 target for a resume chunk), and
  `_split_education` now combines both entries into one 56-token chunk for the
  same reason — the alternative of loosening the chunker's own floor to
  accommodate under-sized pieces would have let real noise back in everywhere
  else just to rescue these two sections.
- Also dropped the `Contact Info` chunk entirely (rather than fixing it to clear
  the floor) — on reflection, phone/email isn't content a public-facing voice
  bot should be citing as a "source" to answer a question, independent of the
  token-count issue; it was borderline even before this bug surfaced.
- Re-ran the full pipeline after the fix: **51 chunks** (9 resume + 8 context.md
  + 34 GitHub), zero under 40 tokens, zero over 500, zero duplicate
  `content_hash` values — comfortably inside `BUILD_PLAN.md`'s 40–150 target.

**Why**

This is the clearest example so far in Phase 2 of why `CLAUDE.md`'s "run it, don't
say it should work" applies at the pipeline level, not just per-file: each loader
looked correct in isolation (`pdf_loader.py` was reviewed and committed on its own
merits, its 15 chunks all read cleanly), and the bug only existed at the seam
between two components that were each individually reasonable — a loader choosing
finer granularity than the spec called for, and a chunker correctly enforcing a
floor neither piece was wrong about in isolation. Only running the whole chain
against real data and reading actual counts surfaced it.

**Decisions made**

- Chunk boundaries for Technical Skills and Education follow "don't lose real
  content" over "match the spec's literal per-category/per-entry granularity" —
  the spec's own resume-skills row already said "one skills block" singular, so
  this is a correction back toward the spec for skills, and a deliberate,
  documented deviation for education (spec says "one education entry," but two
  short entries getting merged into one citable chunk was judged better than
  either losing them or lowering the floor globally).
- `content_hash` incorporates source + section + text, not text alone, so the
  same phrase reused in two different sections still hashes uniquely.

**Verification**

- Ran the full loaders → chunker pipeline against real corpus content (not a
  fixture) twice: once that surfaced the bug (50 chunks, resume chunks
  individually inspected and found wrongly dropped), once after the fix (51
  chunks, zero floor/ceiling violations, zero duplicate hashes).
- Printed every resume chunk's section and token count after the fix to confirm
  all nine are real, meaningful, and within DATA_INGESTION's target range.
- Scanned the diff for secret-shaped strings before staging — none found.
- `git status --short` after staging → the three intended files.
- Committed as `12bb2a1`, separate from this journal entry.

---

## 2026-08-19 — Phase 2: Embedder — verified query prefix, real similarity smoke test

**What happened**

- Before writing `embed_query()`, fetched the actual Hugging Face model card for
  `BAAI/bge-small-en-v1.5` rather than recalling the instruction string from
  memory — `DATA_INGESTION.md` §5 requires it but doesn't quote it verbatim.
  Confirmed the exact recommended string: `"Represent this sentence for
  searching relevant passages:"`, applies to **queries only**, never to stored
  documents, and is explicitly optional in v1.5 (a marginal gain, not a
  correctness requirement — the model card notes v1.5 improved retrieval without
  it). Documented this in the module docstring with the verification source
  named, same as every other "checked the real thing" step this phase.
- Built `ingestion/embedder.py`: `embed_documents()` batch-encodes chunk
  `embed_text` for storage with no instruction prefix; `embed_query()` prepends
  the verified instruction to a query string before encoding. Both request
  `normalize_embeddings=True` per the model's own usage example, and the model
  itself loads once via `lru_cache` rather than reloading per call.
- **Ran a real smoke test** rather than trusting the wiring looked right: embedded
  three short passages — one about the RAG project, one deliberately irrelevant
  ("my favorite pizza topping is pepperoni"), one about JobHunt AI — then embedded
  the query "What are you working on right now?" and computed real cosine
  similarities. The JobHunt AI passage scored highest (0.629 vs. 0.488 and
  0.406), correctly separating a genuinely on-topic passage from an adjacent one
  and a deliberately unrelated one using real vectors, not assumed correct
  because the code ran without error.

**Why**

Checking the model card directly matters for the same reason it's mattered all
phase: a plausible-sounding instruction string recalled from general BGE
familiarity could easily be off by a word or punctuation mark from what this
specific model version actually expects, and a subtly wrong instruction
wouldn't error — it would just quietly under-perform, which is much harder to
notice than a crash. Running the actual similarity comparison (not just checking
that embeddings came back at the right dimension) is what turns "the embedder
runs" into "the embedder retrieves the right thing," which is the property that
actually matters for FR-3.2.

**Decisions made**

- Query instruction prefixing is applied unconditionally at query time, kept as
  a separate `embed_query()` function from `embed_documents()` so the
  query/document asymmetry can never accidentally leak the instruction into
  stored embeddings.
- Model loaded lazily via `lru_cache(maxsize=1)` rather than at import time, so
  importing `embedder.py` (e.g., from a future test) doesn't force a model load.

**Verification**

- Real Hugging Face model card fetched and quoted directly, not recalled.
- Ran `embed_documents()`/`embed_query()` against real text, confirmed 384-dim
  output, and computed real cosine similarities across three passages —
  correct ranking, not just successful execution.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `1d9e3d6`, separate from this journal entry.

---

## 2026-08-19 — Phase 2: Ingest orchestrator — full pipeline run for real, twice

**What happened**

- Filled out `ingestion/ingest.py`: wires all three loaders → `chunker.chunk()` →
  `embedder.embed_documents()` → `supabase-py`'s `.table("chunks").upsert(rows,
  on_conflict="content_hash")`, then the idempotency step 4 from
  `DATA_INGESTION.md` §6 — for every `source` touched this run, delete rows with
  that source whose `content_hash` wasn't in this run's output, via
  `.delete().eq("source", source).not_.in_("content_hash", hashes)`. Checked
  `postgrest`'s actual `SyncFilterRequestBuilder` for the real method names
  (`not_`, `in_`) before writing the call rather than guessing at supabase-py's
  filter chaining syntax.
- **Ran it for real against live Supabase, three separate times, each testing a
  different property:**
  1. First run: 51 chunks upserted across 7 sources. Cross-checked against the
     database directly with `select count(*)` and a per-source breakdown —
     matched the script's own printed summary exactly, and matched the 51-chunk
     count already established at the chunker step. One thing worth naming
     honestly: `Mock-Builder` doesn't appear among the 7 sources — its README is
     genuinely only 22 words, under the 40-token floor, so it produces zero
     chunks. Unlike the Technical Skills/Education bug from the chunker step,
     this isn't a fragmentation artifact to fix — the source content really is
     that thin. No real content gap results: `context.md`'s "A real failure —
     the Mockbuilder project" section already covers that story in full, first-
     person depth.
  2. Re-ran immediately with no changes: still 51 rows, zero duplicates —
     idempotent upsert confirmed against real data, not just inferred from the
     `on_conflict` clause being present in the code.
  3. Manually inserted a fake row directly into the live table (a bogus
     `content_hash` not present in any real run's output, borrowing an existing
     row's embedding just to satisfy the `NOT NULL` column) to create a genuine
     stale-row scenario, then re-ran ingestion. It reported "Deleted 1 stale
     rows"; queried the database directly afterward and confirmed the fake row
     was actually gone and the total was back to exactly 51 — the deletion path
     was exercised against something real, not just present in the code and
     assumed to work.

**Why**

Idempotency and stale-content removal are exactly the kind of logic that looks
obviously correct on the page and is genuinely easy to get backwards (delete too
much, delete too little, or delete rows from a source that wasn't even part of
this run) — `CLAUDE.md`'s "run it, don't say it should work" applies with extra
force here because a *silent* bug in this specific logic (e.g., deleting rows
from every source instead of just the one being re-ingested) wouldn't show up as
an error, it would just quietly corrupt the corpus over successive runs. Faking a
stale row deliberately, rather than waiting for a real content change to test the
path, made the property checkable on demand instead of hoping it would come up
naturally.

**Decisions made**

- Stale-row deletion is scoped per-source, computed from the actual set of
  sources touched in *this* run — a source that wasn't re-ingested this run
  (e.g., if a loader failed) correctly keeps its existing rows rather than
  having them deleted for "not appearing" in a run that never touched them.
- `Mock-Builder` staying at zero chunks is accepted as correct behavior, not
  patched around — logged here so it reads as a understood outcome if it comes
  up again, not rediscovered as a mystery.

**Verification**

- Three full real runs against live Supabase (initial, idempotency re-run,
  fake-stale-row re-run), each cross-checked with direct SQL against the
  database rather than trusting the script's own printed summary.
- Scanned the diff for secret-shaped strings before staging — none found (the
  script reads `DATABASE_URL`/`SUPABASE_URL`/`SUPABASE_SERVICE_KEY` from the
  environment, never contains them).
- `git status --short` after staging → only `ingestion/ingest.py`.
- Committed as `998fc4e`, separate from this journal entry.

---

## 2026-08-19 — Phase 2: Validation surfaces a real retrieval bug — hybrid search added

**What happened**

- Built `ingestion/validate.py`: structural assertions (chunk count in the 40–150
  range, no floor/ceiling violations, no null `source`/`section`, correct 384-dim
  embeddings, no duplicate `content_hash`) plus the 5 spot-check queries from
  `DATA_INGESTION.md` §9, written against the real corpus content rather than
  generic placeholders — e.g. "What was hard about your RAG project?" targets the
  Self-Reflective RAG hard-problem section specifically — plus the deliberately
  out-of-scope "What's your favorite pizza topping?" query that's supposed to
  hit `no_match`.
- **First real run surfaced a genuine bug, not a test artifact.** "What's your
  CGPA?" never returned the Education chunk (the one that literally says "CGPA:
  7.6") in the top 4 — it scored 0.530, which cleared the similarity threshold
  fine, but four unrelated GitHub README chunks happened to score marginally
  higher (0.543–0.557) on pure dense-vector similarity, pushing it out of the
  top-k cutoff. Separately, the out-of-scope pizza query returned 4 results at
  the untested `RETRIEVAL_THRESHOLD=0.35` default that had been sitting in
  `.env` since Phase 0 — real out-of-scope similarity scores against this corpus
  top out around 0.457, well above 0.35.
- Explained both findings to the owner rather than silently patching them — the
  CGPA case specifically needed unpacking, since "why does a GitHub repo outrank
  the actual answer" isn't obvious without understanding that dense embeddings
  compress a whole passage into one vector and are structurally weak at
  anchoring on a specific short acronym buried inside it, versus README prose
  that a small 33M-parameter model can extract more (coincidentally similar-
  scoring, but wrong) signal from.
- Owner asked directly whether the retrieval architecture itself was "naive" and
  wanted the real options laid out: hybrid (dense + keyword) search, cross-
  encoder reranking, a larger embedding model, and query expansion, each with
  concrete merits/demerits given this project's constraints (free tier, a
  voice-agent latency budget already measured as tight in Phase 1, Supabase
  Postgres already available). Recommended hybrid search specifically because it
  fixes this exact failure class (acronyms/names/numbers dense embeddings
  under-weight) using infrastructure already present (Postgres full-text search)
  with no added per-query latency, unlike reranking. Owner chose hybrid search.
- **Implemented it in `match_chunks` itself**, not as a parallel function —
  added a generated `tsvector` column (`text_search`, populated automatically by
  Postgres from `text` on every insert, no ingestion-code change needed) and a
  GIN index, then rewrote the SQL function around a deliberate two-stage design:
  dense cosine similarity still decides *eligibility* (a chunk must clear
  `match_threshold` on real semantic similarity to be considered at all — this
  is unchanged, unweakened, still exactly what ADR-004's anti-hallucination gate
  requires), and only *among already-eligible candidates* does Reciprocal Rank
  Fusion (combining dense rank and `ts_rank_cd` keyword rank, `1/(60+rank)` per
  the standard RRF constant) decide final order. This was a deliberate design
  choice over a single blended score: a keyword hit alone can never rescue a
  chunk that never cleared the real similarity bar, keeping the threshold gate's
  meaning exactly what the spec says it should be.
- Also tuned `RETRIEVAL_THRESHOLD` from 0.35 to 0.5 based on the real observed
  noise ceiling (~0.46 for genuinely unrelated content against this specific
  corpus and embedding model), updating both `.env` and `.env.example` (with a
  comment explaining where 0.5 came from, so a fresh clone doesn't inherit an
  unverified placeholder the way this one did).
- Re-ran the full validation suite after the fix: **all 5 spot-checks now pass**,
  including CGPA (Education chunk now ranks #1 via the keyword boost, even
  though its raw dense similarity is still lower than several competitors), and
  the out-of-scope query still correctly returns `no_match` — the gate wasn't
  weakened by adding the keyword signal.

**Why**

This is the clearest instance yet of why `DATA_INGESTION.md` §9 insists on
validating "at the data layer" before touching the voice pipeline: a retrieval
ranking bug that would have surfaced as an inexplicable refusal deep inside a
live voice conversation (Phase 3+) was instead caught, understood, and fixed
with a SQL query and a printed table, in minutes rather than a debugging session
under time pressure later. The architecture conversation mattered for a
different reason: the owner asked a direct, well-formed question about whether
the system was using a weak algorithm, and answering it honestly (yes, pure
dense retrieval has a well-known blind spot, here's what actually fixes it and
what each option costs) is what let them make a real, informed trade-off call
instead of either blindly accepting "it's fine" or over-correcting to the
heaviest available fix (reranking) without knowing it would cost latency this
project can't currently spare.

**Decisions made**

- `match_chunks` now requires a `query_text` parameter alongside
  `query_embedding` — a breaking change to the RPC's signature, applied now
  while only `validate.py` calls it, specifically so Phase 3's `retrieval.py`
  is written against the final contract from the start rather than needing a
  second migration later.
- Hybrid search's keyword signal can only reorder eligible candidates, never
  admit an ineligible one — the anti-hallucination threshold gate's semantics
  (ADR-004) are treated as non-negotiable, not something a ranking improvement
  gets to quietly loosen.
- `RETRIEVAL_THRESHOLD=0.5` is the new default, empirically grounded rather
  than carried over from an unverified placeholder — still explicitly subject
  to further tuning in Phase 3 against the full `TEST_PLAN.md` question set,
  same as before.

**Verification**

- Ran `validate.py` against live Supabase three times: once with the original
  dense-only `match_chunks` at the old threshold (surfaced both bugs), once
  after tuning the threshold alone (fixed the out-of-scope gate, left CGPA
  failing), once after adding hybrid search (all 5 spot-checks plus the
  out-of-scope check pass).
- Confirmed the new `text_search` column and its GIN index actually exist and
  are populated on real rows via direct `information_schema`/`pg_indexes`
  queries after re-running `setup_db()`, not assumed from the DDL succeeding.
- Structural validation (chunk count, floor/ceiling, nulls, dims, duplicate
  hashes) re-confirmed passing after the schema change.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `750b2e8`.

---

## 2026-08-19 — Phase 2: Reconciling ARCHITECTURE.md with what actually got built

**What happened**

- Amended `ADR-002` and `ADR-003` with dated notes explaining the GitHub REST-vs-MCP
  decision from earlier this phase, cross-referenced between the two ADRs rather than
  duplicated. Deliberately left the original ADR text and "official MCP" framing
  untouched — same convention this journal already follows (see the earlier
  newest-first→oldest-first reordering entry): a decision that got revisited is
  recorded as an amendment on top of the original reasoning, not a silent rewrite that
  erases why the first call was made.
- Filled in `ADR-004`'s Outcome section with the real threshold value (`0.5`) and how
  it was actually derived (measured real out-of-scope similarity scores against this
  corpus, not guessed), plus an explicit note distinguishing what the threshold gate is
  actually responsible for (eligibility) from what hybrid search fixes (ranking) — the
  two validation-step bugs earlier today were different failure classes, and conflating
  them in the writeup would misrepresent which mechanism fixed which problem.
- Filled in `ADR-006`'s Outcome section with the real `bge-small` limitation the CGPA
  spot-check surfaced, and explained why the fix was hybrid search rather than a bigger
  embedding model — the ADR's original "immaterial for a corpus of this size" trade-off
  claim needed a real caveat attached now that there's a concrete counter-example, not
  left standing as an untested assumption.
- Corrected `ARCHITECTURE.md` Sec5's repository layout and Sec6's data model table to
  match the schema actually implemented rather than the original sketch: `id` is
  `bigserial`, not `uuid` (nothing needs cross-system-unique IDs here); the citable text
  column is named `text`, matching `DATA_INGESTION.md`'s own metadata table, not
  `content` as this doc originally sketched; added the `text_search` column and its GIN
  index; updated `ingestion/`'s file listing to include `schema.sql`, `validate.py`,
  and `types.py`, and fixed the stale `github_mcp` filename reference.

**Why**

An architecture document that describes a system different from the one actually
running stops being useful the first time someone — the owner during interview prep,
or a fresh Claude Code session with no memory of this conversation — reads it and
builds a mental model that doesn't match reality. `CLAUDE.md`'s whole reason for
existing is fast, accurate re-orientation; a stale ADR or a data model table with the
wrong column names actively works against that. Doing this reconciliation now, at the
end of Phase 2 rather than deferred to the Phase 6 writeup pass, keeps the gap from
compounding across three more phases of code that would otherwise all cite an
inaccurate schema.

**Decisions made**

- ADR outcomes get filled in as real findings land, not batched for Phase 6 — Phase
  6's "fill in all ADR Outcome fields with real numbers" instruction in `BUILD_PLAN.md`
  is about final review and polish, not about this being the first time numbers get
  written down.
- Documentation amendments are their own commit, separate from the code change that
  motivated them — same log-then-commit discipline applied to docs-about-code as to
  the code itself.

**Verification**

- Re-read the full amended ADR-002 through ADR-006 sections top to bottom to confirm
  the amendments read coherently alongside the original text, not just individually
  correct in isolation.
- Cross-checked the corrected data model table against the real `ingestion/schema.sql`
  column-by-column.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `c0fe898`, separate from this journal entry.

---

## 2026-08-19 — Phase 2: Marked complete in CLAUDE.md status

**What happened**

- Checked off Phase 2 in `CLAUDE.md` and rewrote "Now working on" to point at Phase 3
  (grounding and citations — the graded feature), summarizing where the corpus and
  retrieval layer actually landed: 51 chunks live in Supabase across the resume,
  `context.md`, and 6 curated GitHub repos, ingestion re-runnable and idempotent,
  retrieval hybrid (dense + keyword) rather than the naive dense-only design it started
  the phase with.
- Carried forward four open items rather than letting Phase 2's close bury them: the
  two still-unresolved Phase 1 numbers (LLM latency, barge-in timing — unchanged, still
  waiting on Phase 3's real prompt), plus two new Phase 2 findings that are real but
  explicitly not fully closed — `RETRIEVAL_THRESHOLD=0.5` is empirically grounded but
  still interim pending the full 20-question test set, and `bge-small`'s demonstrated
  acronym-anchoring weakness (the CGPA case) is compensated for by hybrid search in the
  one case that was actually tested, not proven fixed in general.
- Recorded this session's two biggest decisions in the status block itself, not just
  buried in individual journal entries: GitHub ingestion via plain REST rather than an
  MCP client, and the curated (not exhaustive) repo list — both real architectural
  calls a fresh session would need to know about immediately, not rediscover by reading
  every entry above this one.

**Why**

Same reasoning as the Phase 0 and Phase 1 equivalent entries: `CLAUDE.md`'s status
section exists specifically so a session with zero memory of this conversation — a
different Claude Code session, or the owner returning after a break — can get oriented
in under a minute. That only holds if the section is rewritten the moment a phase
actually closes, with the real open threads named explicitly rather than implied.

**Decisions made**

- None beyond the status rewrite itself.

**Verification**

- Re-read `BUILD_PLAN.md`'s Phase 2 exit criteria list against what was actually
  verified this phase, one by one, before checking the box: 40–150 chunks (51, in
  range) ✓, every chunk has meaningful `source`/`section` (verified via
  `validate.py`'s structural checks) ✓, re-running produces zero duplicates (verified
  three times against live Supabase in the ingest-orchestrator step) ✓, all 5 spot-
  check queries return the correct top chunk (true only after the hybrid-search fix —
  honestly false before it) ✓, out-of-scope query scores below threshold (true only
  after the threshold retune — honestly false before it) ✓. Every box reflects a real,
  live-verified result, not an assumption.
- Scanned the diff for secret-shaped strings before staging — none found.
- `git status --short` after staging → only `CLAUDE.md`.
- Committed as `638243f`, separate from this journal entry.

---

## 2026-08-20 — Phase 3: `retrieval.py` — query embedding, hybrid search, threshold gate

**What happened**

- Implemented `agent/retrieval.py`, the first piece of the grounding layer: a single
  async function, `retrieve(query: str) -> dict`, that embeds the query, runs it
  against Supabase's `match_chunks` RPC (the hybrid dense+keyword function Phase 2
  built), and returns the exact `CITATION_SPEC.md` Sec3 contract — `status: "match"`
  with up to `RETRIEVAL_TOP_K` chunks, or `status: "no_match"` with an empty result
  set and the refusal `instruction` string sitting inside the returned data itself,
  not only the system prompt.
- Reused `ingestion/embedder.py`'s `embed_query()` rather than re-implementing query
  embedding — same model, same query-instruction prefix, one place that logic lives.
  Reused the same `match_chunks(query_embedding, query_text, match_threshold,
  match_count)` RPC signature `ingestion/validate.py` already calls, so query-time
  retrieval and Phase 2's validation spot-checks are provably exercising the identical
  code path on the database side.
- The one piece of real design work: `embed_query()` (CPU-bound `sentence-transformers`
  inference) and supabase-py's `.rpc().execute()` (a synchronous HTTP call — the
  installed `supabase` package ships no async client) are both blocking calls. Called
  directly from inside an `async def` in the LiveKit worker, either one would stall the
  worker's single event loop for its duration — not just the current room's turn, but
  audio processing for every other room the worker happens to be servicing
  concurrently. `retrieve()` pushes the whole embed+query sequence into a thread via
  `asyncio.to_thread`, so the event loop stays free while it runs. This is exactly the
  kind of latency-budget concern `SRS.md` NFR-1.3 (retrieval < 100ms) and NFR-1.1/1.2
  (end-to-end latency targets) are about — a blocking call here wouldn't just miss its
  own budget, it would silently tax every other in-flight conversation too.
- Added the config `retrieval.py` needed to `agent/config.py` rather than reading
  `os.environ` locally: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `RETRIEVAL_THRESHOLD`
  (default `0.5`, carrying forward Phase 2's empirically-grounded value),
  `RETRIEVAL_TOP_K` (default `4`), and `OWNER_NAME` (needed by Phase 3's next step, the
  system prompt, so added now rather than in a second pass). Kept `DATABASE_URL` as
  ingestion-only — query-time retrieval only ever calls the `match_chunks` RPC through
  PostgREST, never opens a direct Postgres connection, so there's no DDL/raw-SQL need
  at request time the way ingestion's `setup_db()` has.

**Why**

`CITATION_SPEC.md`'s whole argument is that a citation has to be "a record of what the
system actually retrieved, not a claim the language model makes about its sources" —
that only holds if the retrieval layer is the single place chunks get selected and
scored, with nothing upstream (the LLM, the prompt) able to influence which chunks
"count." Building `retrieval.py` as a standalone module with one clear return contract,
before writing the tool wrapper or the agent class that calls it, keeps that boundary
real in the code, not just in the docs: the tool method in `twin_agent.py` (next step)
will call `retrieve()` and hand back exactly what it returns — no reshaping, no
LLM-visible step in between where the contract could leak.

**Decisions made**

- Query-time retrieval talks to Supabase via the same `supabase-py` REST/RPC client
  ingestion already uses, not a raw `psycopg` connection — no DDL happens at request
  time, so there's nothing a direct Postgres connection buys here that the RPC client
  doesn't already give, and it keeps `DATABASE_URL` (a more powerful credential) out of
  the runtime worker's environment entirely.
- Blocking work (embedding + the RPC call) is wrapped in `asyncio.to_thread` rather than
  left as a direct call in an `async def` — a deliberate, non-obvious choice made before
  it could cause a hard-to-diagnose cross-room latency bug once concurrent visitors are
  real ish (Gemini free tier's ~10 RPM ceiling in `ARCHITECTURE.md` Sec7 already implies
  more than one visitor is a real near-term case, not a hypothetical).
- `RetrievedChunk` is a `TypedDict`, not a dataclass or bare dict-in-comment — cheap
  self-documentation for the shape the tool layer and citation layer both consume next,
  with no runtime cost.

**Verification**

- Ran `retrieve()` live against the real Supabase corpus (not mocked) for both branches:
  `"What are you working on right now?"` → `status: "match"`, 4 results, top scores
  0.55–0.62, correct chunks (`context.md` "What I'm working on right now", Job-Hunt-AI
  roadmap) — matches Phase 2's own spot-check expectations for this query.
  `"What's your favorite pizza topping?"` → `status: "no_match"`, empty results,
  instruction string present — the out-of-scope refusal gate holds at the module level,
  same as it did in `validate.py`'s check, now exercised through the actual code path
  the running agent will use.
- Confirmed both branches return exactly the field names `CITATION_SPEC.md` Sec3
  specifies (`source`, `source_type`, `section`, `text`, `score`, `source_url` on
  match; `status`/`results`/`instruction` on no_match) by inspecting the live output,
  not just by reading the code.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `deff45e`, work only — this journal entry is the separate commit that
  follows it, per `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-20 — Phase 3: TwinAgent, citations.py, and the real system prompt

**What happened**

- Wrote the real content of `agent/prompts/system_prompt.md` — the grounding and
  voice contract from `CITATION_SPEC.md` Sec5, verbatim, with `[NAME]` left as a
  literal placeholder in the file rather than baked to a real name. The prompt is
  meant to stay editable without touching code (`CLAUDE.md`'s Key Files table calls
  it out specifically: "editable, not in code"), so the substitution happens at load
  time, not at file-authoring time.
- Implemented `agent/twin_agent.py`'s `TwinAgent(Agent)`: `_load_instructions()` reads
  that prompt file and does the one substitution (`[NAME]` → `config.OWNER_NAME`),
  and `search_my_background` is a `@function_tool`-decorated method (SDK's "Style B" —
  see `docs/SDK_NOTES.md` Sec2) with the exact docstring `CITATION_SPEC.md` Sec3
  specifies, since the decorator parses the docstring into the description the LLM
  actually reads to decide when to call the tool — it's API contract text, not a
  comment.
- Implemented `agent/citations.py`'s `publish(turn_id, query, retrieval_result)`:
  reshapes whatever `retrieval.py`'s `retrieve()` returned into the exact wire schema
  `CITATION_SPEC.md` Sec4 defines, and sends it over the data channel via
  `get_job_context().room.local_participant.publish_data(..., topic="citations")` —
  the pattern `docs/SDK_NOTES.md` Sec3 verified against the installed SDK rather than
  assumed. On `no_match`, `sources` is built from an empty `results` list, so it comes
  out `[]` — not omitted, not null — which is what lets the frontend's eventual
  citations listener tell "no sources for this turn" apart from "sources not sent yet"
  (FR-4.6 needs that distinction to clear stale cards correctly).
- Wired the two together inside `search_my_background`: retrieve, then `await
  citations.publish(...)`, then return the same result to the LLM as the tool's return
  value. Used `context.speech_handle.id` — a real per-turn identifier the SDK already
  assigns to every assistant turn (confirmed by reading `SpeechHandle`'s source, not
  assumed) — as `turn_id`, instead of inventing a second counter that would have to be
  kept in sync with the SDK's own turn bookkeeping for no reason.

**Why**

The ordering inside `search_my_background` — publish, *then* return — is the actual
mechanism behind ADR-005's "citations published before generation" claim, not just a
docs statement. The tool's return value is what the LLM sees and composes its spoken
reply from; nothing about *generating that reply* can happen until the tool call
returns. So awaiting `citations.publish()` before the `return result` line is what
structurally guarantees the data-channel message reaches the room before the LLM has
produced a single token of the answer it supports — the ordering isn't a convention to
remember, it's enforced by the fact that Python doesn't reach `return` until the
`await` above it finishes.

**Decisions made**

- `[NAME]` substitution happens in `twin_agent.py`, not by hand-editing the prompt
  file with the real name — keeps `system_prompt.md` reusable/shareable without
  embedding personal identity into the one file `CLAUDE.md` singles out as the
  editable grounding contract.
- `citations.publish()` takes `retrieval_result` as a plain dict (the exact shape
  `retrieve()` returns) rather than a shared typed object between the two modules —
  the CITATION_SPEC.md Sec3 and Sec4 schemas are deliberately different shapes (Sec3
  is the tool contract the LLM sees; Sec4 is the wire schema the frontend sees), and
  keeping them as two separate, independently-verifiable transformations matches that
  intentional difference rather than papering over it with one shared type.

**Verification**

- Instantiated `TwinAgent()` directly and confirmed: `instructions` contains the real
  owner name with zero remaining `[NAME]` occurrences; `a.tools` has exactly one
  discovered tool; its `.info.name` is `search_my_background` and `.info.description`
  matches `CITATION_SPEC.md` Sec3's docstring exactly — the auto-discovery path
  (`Agent.__init__` scanning for `@function_tool` methods, per `SDK_NOTES.md` Sec2)
  works as documented, not assumed.
- Ran the real `retrieve()` → `citations.publish()` sequence end to end (with a fake
  `get_job_context()`/room standing in for the LiveKit room, since no live session
  exists yet outside a real call) for both a match and a no_match query, and inspected
  the actual JSON that would go out on the data channel: field names, nesting, and the
  `no_match` → `"sources": []` shape all match `CITATION_SPEC.md` Sec4 exactly.
- Did not yet run this inside a live `AgentSession`/real LiveKit room — `main.py`
  still runs Phase 1's placeholder `Agent`, not `TwinAgent`. That's the next step
  (`BUILD_PLAN.md` Day 3 item 4, "test by voice: does it retrieve, ground, and
  refuse?") and needs `main.py` rewired plus an actual voice session, not just this
  module-level verification.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `7914376`, work only — this journal entry is the separate commit that
  follows it, per `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-20 — Phase 3: wired `main.py` to `TwinAgent`

**What happened**

- Swapped Phase 1's placeholder `Agent(instructions="...generic pipeline-check
  persona...")` out of `agent/main.py`'s entrypoint for `TwinAgent()` — the real
  grounded persona built over the last two steps is now what actually joins the room,
  not just what's importable and unit-verifiable.
- Removed the now-unused `Agent` import from `main.py` (nothing there constructs a
  bare `Agent` anymore; `TwinAgent` is imported from `.twin_agent` instead).
- Updated the FR-1.6 greeting instructions passed to `session.generate_reply()` to
  introduce the persona by `config.OWNER_NAME` and invite background questions,
  instead of the old "say you're ready to chat" placeholder text that made no
  reference to who the visitor is actually talking to.
- Left a short comment at the greeting call-site noting *why* it's safe for the
  greeting not to trigger retrieval: the greeting instruction carries no factual claim
  about the owner, so `system_prompt.md`'s own rule ("do not call the search tool for
  greetings, thanks, or clarifying questions") is what keeps this specific
  `generate_reply()` call from firing `search_my_background` — this is enforced by the
  prompt, not by anything special in `main.py`'s code.

**Why**

Everything built in the previous two steps (`retrieval.py`, `TwinAgent`,
`citations.py`) was correct in isolation but literally could not run — `main.py` was
still constructing Phase 1's disposable placeholder `Agent` and handing that to
`session.start()`. Wiring it is a small diff, but it's the one change that turns three
separately-verified modules into an actual running voice agent for the first time.
This is also the natural point to stop and hand off: everything downstream of this
(does the tool actually get called mid-conversation, does the citation show up on a
real data channel subscriber, does the refusal sound natural spoken aloud) requires an
actual microphone and a human on the other end of the conversation — not something
verifiable by running a script.

**Decisions made**

- None beyond the wiring itself — this step deliberately didn't touch retrieval
  logic, the prompt contract, or the citation schema, to keep the diff isolated to
  "is the real agent now reachable," matching `CLAUDE.md`'s "one phase at a time"
  discipline at the level of individual build-plan items, not just whole phases.

**Verification**

- Ran `python -c "import agent.main"` and confirmed: the module imports cleanly end to
  end (no import errors from the `TwinAgent`/`retrieval`/`citations` chain now pulled
  into `main.py`), `server` is a real `AgentServer` instance, and `entrypoint` is
  registered as expected — exit code 0.
- Did **not** run a live voice session against LiveKit Cloud — that requires a
  microphone and a human conversing with the agent in real time (`BUILD_PLAN.md` Day 3
  item 4's actual "test by voice" step), which isn't something this session can do
  itself. Import-level verification confirms the wiring is structurally correct; it
  does not confirm the tool actually fires mid-conversation, that a real citations
  payload lands on a subscribed client, or that refusals sound right spoken aloud.
  Flagging this explicitly rather than letting "it imports" quietly stand in for "it
  works" — per `CLAUDE.md`'s "run things, don't say this should work" rule, the
  honest status is: wired and import-verified, not yet voice-tested.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `f99d195`, work only — this journal entry is the separate commit that
  follows it, per `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-20 — Phase 3: first live voice test — silent hang traced to a Gemini 429, exposes missing FR-7.2 fallback

**What happened**

- Ran the worker for real for the first time (`uv run python -m livekit.agents start
  agent/main.py`), confirming it registers with LiveKit Cloud (`registered worker`,
  region India South) — Phase 1's "worker connects and logs registered" criterion,
  now re-verified against the actual `TwinAgent`, not the Phase 1 placeholder.
- Discovered along the way that `python -m livekit.agents console --connect-addr`
  is **not** a standalone local-console flag the way older tutorials describe — reading
  `livekit/agents/cli/cli.py`'s `_run_tcp_console` directly (its own docstring: "Run
  console in TCP mode — connects to the Go CLI's TCP server") showed it now expects a
  TCP address served by the separate `lk` Go CLI, not something you pass a bare
  `start`-style invocation to. `docs/SDK_NOTES.md` Sec7 had flagged confirming this as
  an open follow-up back in Phase 1 and never resolved it; resolved now, for real, by
  reading the installed source rather than guessing. The actual test path that works:
  `start` (connects the worker outbound to LiveKit Cloud, same as production) plus
  LiveKit Cloud's newer **Agent Console** (replacing the old hosted Agents Playground —
  confirmed via LiveKit's own docs, since UI navigation is exactly the kind of thing
  that goes stale between a tutorial's publish date and now), reached from the
  project dashboard's Agents section → **Launch Console**.
- First real conversation: greeting exchange worked ("Hi, I'm audible?" → answered),
  but `llm_ttft` was already 7.4s because the call needed two retries against a
  `503 UNAVAILABLE` ("model currently experiencing high demand") before succeeding.
  The very next turn ("Introduce yourself. In short.") — which the grounding prompt
  correctly routes through `search_my_background`, since "introduce yourself" is a
  factual claim about the owner's background — hit a genuine `429 RESOURCE_EXHAUSTED`:
  `generativelanguage.googleapis.com/generate_content_free_tier_requests` capped at
  **5 requests/minute** for `gemini-3.7-flash`, the model `GEMINI_MODEL=gemini-flash-
  latest` currently resolves to. The plugin retried three more times internally (0.1s,
  2s, 2s backoff) and then raised `APIConnectionError: failed to generate LLM
  completion after 4 attempts`. `agent_state` dropped from `thinking` back to
  `listening` with nothing spoken — from the owner's side, indistinguishable from an
  infinite hang, because nothing tells the visitor anything went wrong.

**Why this matters**

Two distinct findings came out of one test session, and they need to stay distinct
rather than getting collapsed into "the rate limit broke it":

1. **A documentation correction.** `CLAUDE.md`'s stack table and `ARCHITECTURE.md`
   Sec7's "known boundaries" both currently say Gemini free tier is "~10 RPM." The
   real, live-observed number for whatever `gemini-flash-latest` resolves to right now
   (`gemini-3.7-flash`) is **5 RPM** — half of what's documented, and easy to exceed
   with nothing more than a greeting plus one grounded question in the same minute,
   especially once 503 retries are also counted against it. This is a platform
   constraint to document accurately, not a bug to fix in this codebase.
2. **A real gap against `SRS.md` FR-7.2**, independent of what triggered it this time.
   FR-7.1 ("retry with exponential backoff and jitter") is effectively already covered
   by the `livekit-plugins-google` plugin's own built-in retry behavior, observed live
   in this session's log. FR-7.2 ("if retry exhausts, the agent SHALL speak a graceful
   fallback message... SHALL NOT fail silently") is **not** implemented anywhere in
   `agent/main.py` or `twin_agent.py` — there is currently no code path that catches an
   exhausted-retry LLM failure and says anything to the visitor. The 429 is what
   *exposed* this gap today; a slow network blip or a transient Deepgram outage would
   trip the identical silent-failure path later, rate limit or not. Diagnosing the
   report as "found a rate limit" alone would have missed the actual product defect
   underneath it.

**Decisions made**

- None yet — diagnosis only, logged before any fix, per the owner's explicit
  instruction to log this finding first. The FR-7.2 fallback implementation and the
  RPM documentation correction are both proposed next steps, not yet built.

**Verification**

- Root cause confirmed directly from the worker's own structured JSON logs for this
  session (`console-3c384518`), not inferred — the exact `429` body, quota metric name,
  and model (`gemini-3.7-flash`) are all present in the captured log, along with the
  timestamps showing the second turn's LLM call failing at 16:20:29 UTC and the
  session going silent (no further assistant turn) until the visitor disconnected at
  16:22:12 UTC.
- Confirmed the `console --connect-addr` finding by reading
  `livekit/agents/cli/cli.py` and `livekit/agents/__main__.py` directly from the
  installed package (`.venv/Lib/site-packages`), not from memory or an external
  tutorial — consistent with `CLAUDE.md` rule 2's verification standard.
- No code changed this entry — nothing to scan for secrets or stage beyond this file.
- This entry is being committed on its own, at the owner's explicit request, ahead of
  any fix — a deliberate, requested exception to the usual "work commit, then journal
  commit" order, made because there is no work commit to sequence it after yet.

---

## 2026-08-21 — Phase 3: FR-7.2 fallback speech, and the RPM documentation correction

**What happened**

- Implemented `agent/main.py`'s `session.on("error")` handler to close the exact gap
  yesterday's live test found: a `session.say(LLM_FALLBACK_MESSAGE)` call, but only
  when the emitted event is an `LLMError` with `recoverable=False`.
- Getting that condition right required reading `livekit/agents/llm/llm.py`'s
  `_main_task` directly rather than guessing at the event shape: every retried attempt
  emits `LLMError(recoverable=True)` first (the individual 503/429 warnings already
  visible in yesterday's log), and only the final, retry-budget-exhausted attempt
  emits `LLMError(recoverable=False)` immediately before raising
  `APIConnectionError`. So the handler fires exactly once per genuinely failed turn —
  not once per retry, which would have meant multiple spoken apologies stacking up
  mid-backoff for a single question. Also read `AgentSession._on_error` (the
  framework's *internal* handler, separate from the public `"error"` event this
  session hook listens on): it turns out `AgentSession` already counts consecutive
  unrecoverable errors and force-closes the session after 3 of them
  (`max_unrecoverable_errors`), but does nothing user-facing *below* that threshold —
  which is exactly the silent-hang gap the live 429 exposed. A single hook on the
  public `"error"` event, filtering to unrecoverable LLM errors, is a complete fix at
  the app layer without needing to touch or override that internal counting logic.
- Corrected the Gemini RPM figure everywhere it was documented wrong: `CLAUDE.md`'s
  stack table, `ARCHITECTURE.md` Sec7's known-boundaries list, and `DEPLOYMENT.md`'s
  free-tier limits table all said "~10 RPM" — the real, live-confirmed number for
  `gemini-3.7-flash` is **5 RPM**. Also corrected `DEPLOYMENT.md`'s accompanying claim
  that the limit is "fine for one visitor" and only a risk with concurrent users —
  false, per yesterday's own test: a single visitor's greeting plus one grounded
  question, with a couple of 503 retries mixed in, was enough to trip it alone.
  Left the original, now-superseded `DEV_JOURNAL.md` entries carrying the old "~10
  RPM" number untouched (2026-08-19's Phase 2 entry, yesterday's Phase 3 diagnosis
  entry) — consistent with this project's own convention of not silently rewriting
  a dated record of what was believed true at the time; the correction lives in the
  living docs (`CLAUDE.md`/`ARCHITECTURE.md`/`DEPLOYMENT.md`) and in this entry, not
  by editing history.

**Why**

Diagnosing the finding without fixing it (yesterday, on request) was step one;
implementing the fix is a different step and deserves its own entry rather than being
folded backward into the diagnosis entry after the fact — same "one phase-item at a
time" discipline this journal has followed all along. The fix itself matters beyond
just "stop the silent hang": FR-7.2 is one of `SRS.md`'s explicit, numbered
requirements, and `NFR-2.2` ("no single pipeline stage failure SHALL terminate the
session without a spoken explanation") is exactly the property a portfolio evaluator
would test for by doing the thing that accidentally happened here — asking a question
right after a greeting, tripping a real rate limit, and watching what the agent does
about it. Better that the honest answer is "it apologizes and asks you to retry" than
"it goes quiet and you have to guess whether it's broken."

**Decisions made**

- The fallback handler is scoped to `llm_error` only, not STT/TTS errors too, even
  though the mechanism (`session.on("error")`, check `.recoverable`) would extend
  trivially to either. FR-7.2's text is specifically about LLM rate limits; FR-7.3
  (vector store unavailability) and FR-7.4 (structured stage-failure logging) are
  separate, distinct SRS requirements not covered by this handler and not asked for
  in this step — scoping the fix to exactly what was requested rather than
  speculatively covering every pipeline stage's failure mode in one pass.
- `LLM_FALLBACK_MESSAGE` is a module-level constant in `main.py`, not moved into
  `agent/config.py` — matches the existing precedent already in this file (the
  greeting instructions are inline too, not centralized), rather than introducing a
  new centralization convention for just this one string.

**Verification**

- Ran `python -c "import agent.main"` after the change — imports cleanly, exit code 0.
- Built a standalone script that constructs a real `AgentSession` (real Deepgram/
  Google/Silero plugin instances, this project's actual config), registers the exact
  handler logic from `main.py`, monkey-patches `session.say` to a capturing stub, and
  emits two real `ErrorEvent`/`LLMError` objects — one `recoverable=True`, one
  `recoverable=False` — through the session's own event emitter (`session.emit`, not
  a mock of it). Confirmed: the `recoverable=True` event produces zero spoken output
  (mid-retry, correctly silent); the `recoverable=False` event produces exactly one
  call to `session.say` with the fallback text. This exercises the real SDK event
  path this handler will see in production, not just the handler function in
  isolation.
- Did not re-run a live voice session to trigger an actual 429 — deliberately, to
  avoid spending more of the same scarce 5-RPM budget confirming a fix for the thing
  that budget just caused. The event-level verification above exercises the identical
  code path a live 429 would trigger; a live re-confirmation is cheap to do next time
  a real conversation happens to trip the limit again.
- Scanned both diffs (code and docs) for secret-shaped strings before staging — none
  found.
- Committed as `2ce1961` (the FR-7.2 handler) and `7551fd2` (the RPM documentation
  correction) — two separate work commits for two separable changes, this journal
  entry committed after both, per `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-21 — Phase 3: switched GEMINI_MODEL to pinned `gemini-3.5-flash-lite`

**What happened**

- Researched a replacement for the 5-RPM `gemini-3.7-flash` at the owner's request:
  "find an LLM with at least 10 RPM and good performance, make sure it's not
  deprecated." Static docs turned out to be useless for this — Google's rate-limits
  page no longer publishes a per-model free-tier RPM table (moved to an
  account-gated AI Studio dashboard), and every third-party blog found via search
  was quoting numbers for the 2.5 generation, which is **entirely dead** for this
  project's account: live-tested `gemini-2.5-flash`, `gemini-2.5-flash-lite`, and
  `gemini-2.5-pro` all return `404 NOT_FOUND: no longer available to new
  users`. Every blog-sourced RPM figure for those three models was therefore moot
  before the comparison even started.
- Determined real numbers the only reliable way left: burst-tested each live 3.x
  candidate directly against the real API (minimal `generateContent` calls, reading
  the quota `limit` back from the `429` error body when one hit) rather than
  guessing. Confirmed: `gemini-3.5-flash` and `gemini-3.7-flash` both cap at 5 RPM
  (full-Flash tier); `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` both sustain
  ≥15 RPM (Flash-Lite tier). Presented both qualifying candidates with pros/cons,
  changed nothing yet, per the owner's explicit "list them, I'll decide" instruction.
- Owner chose `gemini-3.5-flash-lite`, pinned rather than another rolling alias —
  matching the recommendation made alongside the comparison: the alias
  (`gemini-flash-latest`) was supposed to dodge model retirement, but it's exactly
  what silently cut the RPM budget in the first place when Google moved its target
  from a 10 RPM model to a 5 RPM one with zero warning. A pinned ID can only fail
  loudly (404 on retirement), which this project already has a track record of
  catching (the 2.5-generation failures above, and the original Phase 1 finding in
  `docs/SDK_NOTES.md`).
- Before touching any files, discovered the working tree already had a partial,
  **uncommitted** version of this exact switch sitting in `agent/config.py` and
  `.env.example` — dated 2026-08-21, using the `gemini-flash-lite-latest` rolling
  alias, with a comment describing verification testing (15 RPM, correct
  call/skip behavior across three prompts) matching almost exactly what this
  session was about to do independently. This is very likely a prior Claude Code
  session's work that never reached the commit step — consistent with an earlier
  `[SYSTEM NOTIFICATION]` this session received reporting "no completion record...
  may have been stopped... or running when the previous process exited" for an
  unrelated background command. Rather than discard or blindly build on top of
  unfamiliar uncommitted state, read it, confirmed it was sound and consistent with
  this session's own independent findings, and edited it in place to use the pinned
  ID the owner actually asked for instead of the alias it had used — treating it as
  a legitimate draft to correct, not stray junk to delete.
- Independently re-verified the inherited draft's tool-calling claim rather than
  trusting it as written: built a standalone script driving the actual
  `livekit.plugins.google.LLM` plugin with `TwinAgent`'s real system prompt and
  `search_my_background` tool attached (via `LLM.chat(chat_ctx=..., tools=...)`,
  not the raw REST API), and ran three real prompts through it — a greeting, a
  factual question, and the adversarial "you worked at Google, right?" case.
  Confirmed live: the greeting produces zero tool calls, the factual question and
  the adversarial question both correctly trigger `search_my_background`.
- Added `GEMINI_MODEL=gemini-3.5-flash-lite` explicitly to `.env` (it previously had
  no `GEMINI_MODEL` line at all and was silently relying on `config.py`'s code
  default), matching how every other tunable value in this project is set
  explicitly rather than implicitly inherited.
- Separately, made an operational mistake worth recording honestly: while
  inspecting `.env` for the existing `GEMINI_MODEL` line, ran an unredacted `grep`
  that printed the real `GEMINI_API_KEY` value into a tool-output block before a
  planned `sed` redaction ran on a *different* command — the raw key value briefly
  appeared in this session's own transcript. Flagged it to the owner immediately,
  recommended rotating the key in Google AI Studio out of caution, and switched to
  always piping `.env` inspection through redaction from that point on. Recorded
  here rather than quietly fixed and forgotten, since a project this focused on
  "never hardcode secrets" (`CLAUDE.md` rule 1) should have an honest record when
  a secret briefly surfaced somewhere it shouldn't have, even transiently and
  locally.

**Why**

The core lesson repeats the one from yesterday's RPM finding: a rolling alias is
not actually a hedge against model churn, it's a *different* kind of exposure to
it — silent instead of loud. Pinning trades "never have to think about this again"
for "will fail in an obvious, detectable way if Google retires it," which is the
better trade for a project whose whole grounding story depends on knowing exactly
what's running, not on trusting an alias to keep resolving somewhere reasonable.

Re-verifying the inherited draft's claims rather than trusting them as written
matters for the same reason `CLAUDE.md` rule 2 insists on reading the installed SDK
directly rather than reproducing patterns from memory: a comment asserting
something was tested is not the same as it being true *for the code as it exists
right now*, especially content left by a session with no way to hand off context
directly. The independent re-run confirmed the inherited claim was accurate, but
that was worth establishing rather than assuming.

**Decisions made**

- Pinned model ID over rolling alias, reversing this project's own Phase 1
  reasoning now that the alias has caused the exact failure it was meant to
  prevent — see `agent/config.py`'s updated comment for the full chain of
  reasoning kept in the code itself, not just here.
- `GEMINI_MODEL` is now set explicitly in `.env`, not left to the code default —
  closes a small inconsistency where the actually-running model depended on
  reading `config.py` to know, rather than being visible in the environment file
  that's supposed to be the single source of truth for runtime configuration.
- Did not change `RETRIEVAL_THRESHOLD`, `RETRIEVAL_TOP_K`, or any other tuning
  value as part of this — scoped strictly to the model swap the owner asked for.

**Verification**

- Live burst-tested 7 model IDs against the real API before recommending anything;
  results and methodology covered above and in the conversation the owner
  approved before choosing.
- Ran `python -c "from agent import config; assert config.GEMINI_MODEL ==
  'gemini-3.5-flash-lite'"` — confirms `.env`'s new explicit value is what
  `config.py` actually loads, not just what the file says.
- Ran `python -c "import agent.main"` — imports cleanly with the new model wired
  through `main.py`'s `google.LLM(model=config.GEMINI_MODEL, ...)` call site,
  unchanged since Phase 3's earlier wiring step.
- Ran the three-prompt tool-calling test described above through the real
  `google.LLM` plugin and real `TwinAgent` instance — not mocked, not assumed from
  the inherited comment.
- Scanned the diff for secret-shaped strings before staging — none found in the
  staged changes themselves (the transient exposure noted above was in a tool
  output, not anything committed).
- Committed as `b3ee641` — a single commit covering `agent/config.py`,
  `.env.example`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, and `docs/DEPLOYMENT.md`,
  since all five are one coherent change (the model swap and its documentation),
  not separable steps. `.env` itself is gitignored per `CLAUDE.md` rule 1 and was
  updated locally only. This journal entry follows as the separate commit, per
  `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-21 — Phase 3: fixed a 13.79s cold-start latency spike with a prewarm hook

**What happened**

- A second live voice test (after the model switch) felt noticeably faster overall,
  but the owner reported "still felt a lag once." Asked to check the log before
  moving to Day 4 rather than assume it was nothing.
- The log confirmed a real, deterministic problem, not noise: turn 2 ("Introduce
  yourself in short.") — the conversation's *first* grounded (tool-calling)
  question — had `e2e_latency=13.79s`. Turns 3 and 4, also grounded, same session,
  same tool: `4.56s` and `4.18s`. Same code path, 3x slower on the first hit.
- Root cause, read directly from the log rather than guessed: LiveKit spawns a
  fresh OS process per room for isolation (visible as "initializing job runner"
  right when each job dispatches). Inside that fresh process, `retrieval.py`'s
  `_client()` (a `@lru_cache`d `supabase.create_client`) and `embedder.py`'s
  `_model()` (a `@lru_cache`d `SentenceTransformer`) are both lazily constructed on
  first call. The log shows exactly this happening mid-turn: `"No device provided,
  using cpu"` → `"Loading SentenceTransformer model from BAAI/bge-small-en-v1.5."`
  fired right after `agent_state: listening -> thinking` on turn 2, and never again
  in that session — because the `lru_cache` kept the loaded model resident for
  turns 3 and 4, which is exactly why only the *first* grounded turn paid the cost.
- Fix: `AgentServer` accepts a `setup_fnc` (LiveKit's standard hook for exactly this
  class of problem — the framework's own examples use it to preload VAD models),
  which runs once per job-runner process *before* that process accepts any room.
  Added `agent/main.py`'s `_prewarm(proc)`, which calls `retrieval.py`'s own
  `_match_sync("warmup")` — the real embed-plus-RPC code path a live query takes,
  not a reimplementation of it — so both lazy singletons get populated at worker
  startup instead of on a visitor's turn.
- Verified live by restarting the worker and reading its own `worker.log`
  (redirected via PowerShell `tee` for this run, at the owner's suggestion, so the
  full session log could be read directly instead of pasted by hand): the first
  batch of idle job-runner processes each logged `elapsed_time: 8.21`–`8.24` on
  `"job runner initialized"` — that's the prewarm cost, now paid at worker launch,
  before `"registered worker"` even fires. Every idle-pool process spawned *after*
  that first batch initialized in `0.3`–`0.8s`, benefiting from an already-warm OS
  file cache for the model weights. In the actual conversation that followed: the
  greeting was unaffected (`llm_ttft=1.06s`, no tool call), and the first grounded
  question — "What are you currently working on?" — landed at `e2e_latency=2.73s`,
  down from `13.79s` for the equivalent turn before the fix. The owner didn't feel
  any lag on this run.

**Why**

This is the same underlying lesson as the RPM finding two entries back, applied to
a different resource: a lazy-loaded singleton is invisible until something forces
it to load, and whichever caller happens to go first eats a cost that has nothing
to do with that caller's own work. Debugging this from "it felt slow once" to an
exact root cause required reading the raw log rather than re-running the test and
hoping — the `"Loading SentenceTransformer"` line appearing exactly once, exactly
inside the slow turn's `thinking` window, is what turned a vague feeling into a
provable, fixable claim. `setup_fnc` is the right place for the fix specifically
*because* LiveKit already spawns a fresh process per room (a deliberate isolation
choice, not something to fight) — the fix works with that architecture by paying
the cost once per process at a time nobody is waiting on it, rather than trying to
share state across processes or avoid the per-room process model entirely.

**Decisions made**

- Reused `retrieval.py`'s existing `_match_sync` helper for the warmup call instead
  of writing separate prewarm-specific logic to touch the embedder and Supabase
  client individually — one code path, so the thing being warmed is provably
  identical to the thing a real query runs, not a parallel implementation that
  could drift out of sync with it.
- The warmup call's result is discarded — its only job is populating the two
  `lru_cache`s, not producing a usable answer, so there's no result-shape concern
  to worry about matching `retrieve()`'s contract.
- Did not attempt to also prewarm Deepgram/Gemini connections — `google.LLM` and
  the Deepgram plugins already call `.prewarm()` internally as part of
  `AgentSession` construction (confirmed via `docs/SDK_NOTES.md`'s reading of the
  SDK — `agent_session.py` calls `self._llm.prewarm(loop=self._loop)`), so that
  class of cold-start was already handled by the framework; only the project's own
  lazily-loaded singletons (embedder, Supabase client) were the actual gap.

**Verification**

- Live, not simulated: restarted the real worker, ran a real conversation through
  the Agent Console, and read the resulting `worker.log` end to end rather than
  trusting a single spot-checked number.
- Confirmed the prewarm hook fires exactly where expected (inside `setup_fnc`,
  before `"registered worker"`) and confirmed its cost is absorbed by comparing
  first-batch vs. later-batch `job runner initialized` `elapsed_time` values in the
  same log — first batch paid the real cost once; every process after that was
  fast, which is the expected shape if the fix is working and not just coincidence.
  Deferred a second, deliberately controlled test (fresh worker restart, first
  message immediately a grounded question, nothing warmed by prior turns) to a
  later session if the improvement ever needs re-confirming in isolation — this
  session's data was conclusive enough on its own.
- The ~10s increase in the worker's own startup-to-registered latency and the
  leftover Hugging Face Hub warning (unauthenticated requests) are both cosmetic,
  pre-existing side effects of this change or unrelated to it — noted but not
  acted on; the startup delay is a one-time worker-launch cost, never something a
  visitor waits through.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `c2a3435`, work only — this journal entry is the separate commit
  that follows it, per `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-21 — Phase 3 Day 4: threshold tuning found no clean separation exists

**What happened**

- Started Day 4 (per `BUILD_PLAN.md`: frontend citations listener, source cards,
  `no_match` clearing stale cards, threshold tuning). Investigating before
  implementing surfaced that neither the Token Service (`api/main.py`) nor any
  frontend (`web/`) exists yet — both are Phase 0 docstring stubs, and
  `web/README.md` explicitly says frontend work starts in Phase 4, conflicting with
  `BUILD_PLAN.md`'s Day 4 items. Raised this via `AskUserQuestion` rather than
  guessing; owner chose to scaffold a minimal frontend now (room connection +
  citations listener + basic cards only, all UX polish deferred to Phase 4 as
  planned) — that expanded scope went through a full plan-mode pass
  (`EnterPlanMode`/`ExitPlanMode`) before any code was written, given it touches
  multiple new subsystems (Token Service, frontend) the owner should sign off on
  before implementation starts.
- Did threshold tuning first, ahead of the Token Service/frontend, since it needs
  no new infrastructure. Wrote `ingestion/tune_threshold.py`, which sweeps
  `TEST_PLAN.md`'s Suite A/B against the live corpus at a range of threshold values
  by reusing `validate.py`'s existing `_match(client, query, threshold, top_k)`
  helper — the same embed+RPC code path `agent/retrieval.py` uses in production,
  just parameterized by threshold instead of reading the fixed value baked into
  `config.RETRIEVAL_THRESHOLD` at import time. Replaced `TEST_PLAN.md` Suite A's
  generic `[company]`/`[your main project]` placeholders with 13 real questions
  grounded in the actual resume and `corpus/context.md` content (extending
  `validate.py`'s existing 5 `SPOT_CHECKS`), since a meaningful sweep needs real
  expected-answer keywords to check against, not placeholder text.
- The first sweep (0.35–0.55) found something worse than expected: **no threshold
  in that range reached zero Suite B false accepts.** At the current production
  value (0.50), 4 of 7 out-of-scope questions returned results. Widened the sweep
  to 0.70 and diagnosed the specific false accepts directly (which query, which
  chunk, what similarity) rather than just staring at the aggregate counts: three
  of the four false accepts at 0.50 cleared by 0.55 (election/siblings/last-weekend,
  all sub-0.53 similarity, genuinely marginal), but one — "what's your salary
  expectation?" matching an unrelated GitHub README about a *Loan Eligibility & Risk
  Scoring* API's usage docs, at similarity 0.61 — persisted all the way to 0.60 and
  only cleared at 0.65.
- Reaching 0.65 to kill that one anomaly cost **6 of 13** Suite A matches (11/13 at
  0.50 down to 7/13 at 0.65) — `TEST_PLAN.md`'s own stated rule ("choose the lowest
  threshold with zero false accepts") would have mechanically picked 0.65 and
  silently gutted more than half the twin's ability to answer real questions to
  fix one edge case. Diagnosed which Suite A questions actually failed at each
  threshold (not just the count) before concluding anything: most were genuinely
  borderline (0.55–0.62 similarity — "most recent role," "what did you study," "the
  hardest technical problem," current CGPA, "what are you working on") — real
  content, just not comfortably clearing a threshold pushed that high to chase one
  unrelated false accept.
- Given how load-bearing this threshold is — it's the entire structural
  anti-hallucination mechanism ADR-004 describes — surfaced the full trade-off
  table to the owner rather than picking a number unilaterally, with a reasoned
  recommendation (0.55: kills 6 of 7 false accepts, keeps 9/13 Suite A) rather than
  either extreme. Owner confirmed 0.55 via `AskUserQuestion`, and separately chose
  to defer investigating a distinct finding — "What's your most recent role?"
  (`CITATION_SPEC.md` §7's first suggested demo question) failing to retrieve the
  Freelance chunk in the top-4 at *every* threshold tested, a ranking gap unrelated
  to threshold choice — to Phase 6 rather than blocking Day 4 on it now.
- Updated `RETRIEVAL_THRESHOLD` to `0.55` in `.env`/`.env.example`/`agent/config.py`,
  filled in `TEST_PLAN.md`'s threshold table with the real sweep results and an
  explicit note that the stated "lowest threshold, zero false accepts" rule didn't
  hold cleanly here, and amended `ARCHITECTURE.md` ADR-004 with the corrected
  finding (the original "~0.46 noise ceiling" claim was real but based on testing
  only one out-of-scope query; the actual ceiling for this corpus reaches 0.61).
  Rewrote `CLAUDE.md`'s "Now working on"/"Blocked by" status block, which had gone
  stale since the end of Phase 2 despite three full Phase 3 Day 3 sessions and half
  of Day 4 having happened since.

**A secrets-handling incident, recorded honestly rather than quietly fixed.**
While updating `.env`'s `RETRIEVAL_THRESHOLD` line, used the `Read` tool directly on
the full `.env` file to satisfy the Edit tool's precondition of having read a file
before editing it — printing every credential in the project (LiveKit API key and
secret, Deepgram key, Gemini key, Supabase service key, the Supabase database
password embedded in `DATABASE_URL`, and the GitHub PAT) unredacted into this
session's own transcript. This is a repeat of the same class of mistake from
2026-08-20's entry (an unredacted `grep` exposing only the Gemini key that time),
worse in scope this time — every secret, not one. Flagged it to the owner
immediately and recommended rotating all of them. Fixed the underlying edit with
targeted `sed` (`sed -i 's/^RETRIEVAL_THRESHOLD=0.5$/RETRIEVAL_THRESHOLD=0.55/'
.env`) instead, which never prints file contents, and that's the pattern going
forward for any further `.env` edits — the earlier fix (piping `grep` through
`sed` redaction) turned out to be an incomplete mitigation, since it doesn't help
against a direct `Read`. `.env.example` (no real values) remains safe to `Read`
directly; only the real `.env` needs this discipline.

**Why**

The core lesson repeats a shape this project keeps running into: a rule that
sounds clean in the abstract ("lowest threshold with zero false accepts") can
produce a bad outcome when the underlying data doesn't actually separate cleanly —
the same category of finding as the RPM alias and the cold-start prewarm, just
applied to retrieval quality instead of infrastructure. The fix in each case was
the same discipline: don't apply a stated rule mechanically once live data shows
it doesn't hold; diagnose the specific failures, understand *why*, and bring the
real trade-off to whoever's actually accountable for the decision rather than
silently picking whichever number the rule technically outputs.

**Decisions made**

- `RETRIEVAL_THRESHOLD=0.55`, chosen as a deliberate balance rather than a value
  that achieves clean separation — recorded as such everywhere it's documented,
  not glossed over as if 0.55 were simply "the answer."
- `ingestion/tune_threshold.py` kept as a real, reusable tool (not a throwaway
  script) since `CLAUDE.md`'s own status notes already flagged this needing a
  fuller re-run in Phase 6.
- The "most recent role" retrieval gap is logged in three places (`TEST_PLAN.md`
  Suite A note, `CLAUDE.md` status block, this entry) rather than only one, since
  it's exactly the kind of finding that's easy to lose track of across a long
  project if it's only mentioned once.
- Going forward, no `Read` (or unredacted `grep`/`cat`) of the real `.env` file —
  targeted `sed` for edits, and if inspection is ever needed, only through a
  redaction pipe applied to every line, not just the one being changed.

**Verification**

- Ran the sweep live against the real Supabase corpus at 8 threshold values, then
  a second, targeted diagnostic pass per-query to identify exactly which Suite A/B
  questions were failing and why, before drawing any conclusion — not just reading
  the aggregate pass/fail counts.
- Confirmed `agent.config.RETRIEVAL_THRESHOLD == 0.55` after the `.env` change, via
  a fresh Python process reading the actual environment, not assumed from the file
  edit alone.
- Re-read `TEST_PLAN.md`'s and `ARCHITECTURE.md`'s amended sections top to bottom
  to confirm they read coherently and don't overstate the result (explicitly
  calling out that 0.55 is a balance, not a clean fix, in both places).
- Deleted the two ad hoc diagnostic scripts (`_tmp_diag.py`, `_tmp_diag2.py`) used
  to identify specific false accepts/failures — not committed, scratch work only.
- Scanned the diff for secret-shaped strings before staging — none found in the
  staged changes (the transcript exposure noted above was in tool output, not
  anything committed to the repo).
- Committed as `618eae2`, work only — this journal entry is the separate commit
  that follows it, per `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-21 — Phase 3 Day 4: Token Service (api/main.py)

**What happened**

- Verified `livekit.api`'s `AccessToken`/`VideoGrants` builder API directly against
  the installed package (`inspect.signature` on `AccessToken.__init__`,
  `.with_identity`, `.with_grants`, `.with_ttl`, `.to_jwt`, and `VideoGrants.__init__`)
  before writing any code, during this step's plan-mode pass — same discipline
  `CLAUDE.md` rule 2 requires for the LiveKit Agents SDK, applied here to
  `livekit-api` (a transitive dependency already installed, no new package needed
  for the token logic itself).
- Implemented `api/config.py` (new): loads `LIVEKIT_URL`/`LIVEKIT_API_KEY`/
  `LIVEKIT_API_SECRET` only, plus a `FRONTEND_ORIGIN` for CORS defaulting to Vite's
  dev port. Deliberately a separate module from `agent/config.py` rather than
  reusing it — the token service's own docstring promises it never holds a
  database or LLM credential, and importing `agent/config.py` would pull in
  `GEMINI_API_KEY`/`SUPABASE_SERVICE_KEY` even if unused, which is exactly the kind
  of accidental-blast-radius mistake worth designing out at the module boundary
  rather than trusting discipline to avoid later.
- Implemented `api/main.py`: `POST /token` mints a fresh room name
  (`twin-{uuid4().hex[:8]}`) and participant identity
  (`visitor-{uuid4().hex[:8]}`) per call, builds the grants
  (`room_join`/`can_publish`/`can_subscribe`/`can_publish_data`, all `True` — the
  data-publish grant matters because the agent worker publishes citations over the
  data channel into this same room, so the visitor's own grant needs to already
  permit receiving them), and sets a 15-minute TTL (FR-1.3). `GET /health` is a
  trivial 200 OK, doubling as the future keep-warm target (NFR-2.1).
- Added `fastapi` and `uvicorn[standard]` to `pyproject.toml` — the first new
  runtime dependencies added since Phase 1's initial scaffold.
- `NFR-3.4` (per-IP rate limiting on `/token`) explicitly **not** implemented —
  noted in both the docstring and this entry as deferred to Phase 5/6 hardening,
  not silently dropped from scope.

**Why**

This is the first of Day 4's two new subsystems (the frontend is next) and the one
everything else depends on — a browser can't join a room without a token, and
`BUILD_PLAN.md`'s Day 4 items assumed this already existed. Keeping it deliberately
small (one route that matters, one health check, no auth beyond what CORS + TTL
provide yet) matches the actual scope: this is infrastructure to unblock the
citations UI, not a place to front-load Phase 5/6 hardening work that isn't needed
to prove the citations contract end-to-end yet.

**Decisions made**

- `api/config.py` stays a separate module from `agent/config.py`, permanently, not
  just for now — the credential-scoping argument above doesn't go away once the
  frontend exists.
- CORS is open to the Vite dev origin only for now, with an explicit code comment
  and this entry both flagging that it needs tightening before deployment, so it
  doesn't quietly ship permissive.
- Left the running `uv run uvicorn api.main:app --port 8000` process up rather
  than stopping it after verification, since the next step (frontend scaffold)
  needs a live Token Service to fetch tokens from.

**Verification**

- Started the real service (`uv run uvicorn api.main:app --port 8000`) and hit both
  endpoints with `curl` — not a unit test, the actual running server.
- Decoded the returned JWT (via `PyJWT`, signature verification skipped since the
  point was inspecting claims, not re-validating what `to_jwt()` already produced)
  and asserted, against the real decoded payload: TTL is exactly 15 minutes
  (`exp - nbf`), `video.roomJoin`/`video.canPublishData` are both `true`, the room
  name starts with `twin-`, and the URL is a real `wss://` LiveKit Cloud endpoint —
  every FR-1.1–1.3 claim checked against the actual token, not assumed from the
  code reading correct.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `87d32a1`, work only — this journal entry is the separate commit
  that follows it, per `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-21 — Phase 3 Day 4: frontend scaffold + citations listener, verified live

**What happened**

- Scaffolded `web/` with Vite's React-TS template. `npm create vite@latest web --
  --template react-ts` refused non-interactively (`Operation cancelled`) because
  `web/` already had a `README.md` in it from Phase 0 scaffolding — no stdin
  available to answer the "directory not empty" prompt. Worked around it by
  scaffolding into a throwaway `_web_scaffold_tmp/` directory, then moving
  everything except its generated `README.md` into `web/`, preserving the
  project-specific one. Removed the scaffold's unused demo assets
  (`hero.png`/`react.svg`/`vite.svg`) and its leftover `web-scaffold-tmp` package
  name once the merge was done.
- Before writing any component code, verified `@livekit/components-react`'s
  `useDataChannel` hook against the actually-installed package source (not just
  the docs summary from planning) — read
  `node_modules/@livekit/components-react/src/hooks/useDataChannel.ts` and
  `node_modules/@livekit/components-core/src/observables/dataChannel.ts`
  directly: `ReceivedDataMessage<T> = { topic?: T; payload: Uint8Array; from?:
  Participant }`, confirming the `TextDecoder` → `JSON.parse` decode path planned
  earlier was correct. Same discipline `CLAUDE.md` rule 2 requires for the Python
  SDK, applied here to the JS side for the first time this project has needed it.
- Implemented `web/src/types/citations.ts` (the `CITATION_SPEC.md` Sec4 wire
  shape as TypeScript types) and `web/src/components/CitationsPanel.tsx`:
  `useDataChannel("citations", onMessage)`, decode, and render source cards in a
  list keyed by `turn_id`, newest first — deliberately never merging or
  accumulating sources across turns, since rendering each turn's payload exactly
  as received is what makes FR-4.6 hold structurally rather than by convention.
- `App.tsx`: fetches a token from the Token Service on mount, wraps the app in
  `LiveKitRoom`, renders `RoomAudioRenderer` and a minimal `ControlBar` (mic
  toggle only — `chat`/`screenShare`/`leave`/`settings` controls all disabled,
  since none of that is Day 4 scope).
- `npm run build` (which runs `tsc -b` first) passed clean on the first attempt.
- Live end-to-end test, not simulated: started the real Token Service, the real
  agent worker, and the real Vite dev server, then opened the app in the Browser
  pane. First attempt failed immediately — `LiveKitRoom`'s `audio` prop (set to
  `true` to auto-publish the mic on connect) triggered a `NotAllowedError` when
  the Browser pane's sandbox denied microphone access, and the *entire room
  connection* dropped as a result (`disconnect from room` → `connecting ->
  disconnected` in the console), not just the audio publish. That's a real bug
  independent of the sandbox — a real visitor who hesitates on the mic prompt, or
  denies it, would get bounced out of the conversation entirely rather than just
  losing mic input. Removed `audio` from `LiveKitRoom`; the mic is now opt-in via
  `ControlBar`'s own toggle. Re-tested: connection now reaches `connected` and
  stays there regardless of mic permission state.
- The sandbox still blocks mic capture, so a full spoken conversation couldn't be
  driven through this browser tab. Verified the actual thing Day 4 needed to
  prove — the citations wire contract and rendering — a different way: published
  real `match` and `no_match` citations payloads directly into the live room via
  `livekit.api`'s `RoomServiceClient.send_data` (the exact same call
  `agent/citations.py` makes, just invoked from a standalone script instead of
  from inside the running agent), and read the actual rendered page text back.
  Both cases rendered correctly: the match turn showed its real source card
  (`context.md`, score `0.62`, correct excerpt); the later no_match turn got its
  own explicit "No documented source for this question" entry, and the earlier
  match turn's card was still there, untouched, correctly attached to its own
  turn — direct proof FR-4.6 holds, not inferred from reading the component code.
- Separately confirmed the real agent worker actually auto-dispatched into this
  browser tab's room and spoke its real greeting (read straight from the
  worker's own log: `room=twin-21ae791a`, `"session started, sending greeting"`,
  the actual greeting text) — proving FR-1.1–1.6 through this project's own
  frontend and Token Service for the first time; every prior test (Phase 1
  through today) went through LiveKit's own Agent Console instead.
- Updated `web/README.md` from its Phase 0 "not scaffolded yet" placeholder to
  describe what's actually there and how to run it.

**Why**

The `audio` prop bug is worth dwelling on: it wasn't caught by `npm run build`'s
type-check, because it's not a type error — `audio?: boolean` is a perfectly
valid prop, and the failure mode only shows up when a real browser actually
denies the permission at runtime. This is exactly why `CLAUDE.md`'s working
style insists on running things and watching real output, not just getting a
clean compile: a frontend that builds and a frontend that behaves correctly
under a real permission denial are different claims, and only live testing in
an actual browser distinguishes them. The Browser pane's own mic restriction,
which looked like it would block this whole verification step, ended up being
the thing that surfaced the bug in the first place.

**Decisions made**

- Mic capture is opt-in via `ControlBar`, not auto-requested on connect — not
  just a workaround for this session's sandbox, a real UX decision that also
  happens to make FR-1.5 (a proper mic-permission explainer) a Phase 4
  enhancement rather than a Day 4 blocker: the connection no longer depends on
  the mic permission outcome at all.
- `CitationsPanel` stores turns as a plain array, not a map keyed by `turn_id`
  with in-place updates — each `citations` message is already a complete,
  self-contained record of one turn (per `CITATION_SPEC.md` Sec4), so there's
  nothing to merge or update; appending preserves turn order for free and keeps
  FR-4.6 correct by construction rather than by careful update logic.
- Verified the citations contract via direct server-side data publishes rather
  than stopping at "the sandbox blocks mic, so this can't be fully tested" —
  the citations panel doesn't care how a payload arrived, so exercising it with
  the exact same `send_data` call the agent makes is a faithful test of the
  actual thing Day 4 needed to prove, not a lesser substitute for a live voice
  conversation.

**Verification**

- `npm run build` (`tsc -b && vite build`) — clean, zero type errors, zero
  warnings beyond an expected bundle-size note (LiveKit's client is inherently
  large; code-splitting is a Phase 4/5 concern, not a Day 4 one).
- Live browser test via the Browser pane: real token fetch, real LiveKit Cloud
  connection, `connection state changed: connecting -> connected` read directly
  from the browser's own console log, not assumed.
- Real agent dispatch and greeting confirmed by reading the worker's own
  structured log for the exact room ID the browser tab was in.
- Both citations cases (match, no_match) verified by publishing real payloads
  through the real LiveKit data channel and reading back the actual rendered
  page text — not a component-level mock, not code review alone.
- Scanned the diff for secret-shaped strings before staging — none found;
  `web/.env.local` (holding only the non-secret dev Token Service URL) confirmed
  absent from `git status` output, `web/.gitignore` respected.
- Committed as `8eebd82`, work only — this journal entry is the separate commit
  that follows it, per `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-21 — Phase 3 Day 4 closes: owner confirmed a real spoken conversation works

**What happened**

- The owner tested `web/` themselves against `localhost` — a real browser, real
  microphone, a real spoken conversation through this project's own frontend for
  the first time (this session's own testing was data-channel-only, since the
  sandboxed Browser pane blocks microphone capture). Confirmed: **it works.**
  This closes the one piece of Phase 3's exit criteria that specifically needed a
  human with a working microphone rather than anything scriptable — `CLAUDE.md`'s
  "Next up" note from the previous entry named this exact gap.
- Feedback alongside the confirmation: the UI "looks like shit" and needs
  significant visual work. Expected, not a surprise finding — `web/README.md`,
  `CLAUDE.md`'s status block, and every commit message touching `web/` this
  session have said the same thing in the same words: Day 4 built room
  connection, a citations listener, and a plain unstyled mic toggle, nothing
  more, with all visual polish explicitly deferred to Phase 4. The owner's
  reaction confirms that plan was correctly scoped, not that something went
  wrong — Phase 4's UX pass is exactly where this gets addressed, not a
  surprise addition to the backlog.
- Stopped all three processes left running from the previous session
  (Token Service, agent worker, Vite dev server) at the owner's request now that
  live testing is done for this session. Found the same orphaned-child-process
  pattern as an earlier session's worker cleanup: `TaskStop` cleanly killed the
  Python processes (Token Service, worker) but left `npm run dev`'s child `node`
  process (running `vite.js`) still alive after its parent `npm-cli.js` process
  was stopped — confirmed via `Get-CimInstance Win32_Process`, force-killed both
  PIDs directly, then re-checked the process list came back empty.

**Why**

Worth recording as its own entry rather than folding into the previous one: the
previous entry's "Verified" section was honest that mic-based conversation
*hadn't* been tested by this session, only citations-over-data-channel. Closing
that gap is a distinct, real event — the first actual end-to-end proof, by a
human, that voice in, grounded answer, voice out, citations rendered all works
together through this project's own infrastructure rather than through LiveKit's
Agent Console. That deserves its own dated record, not to be quietly absorbed
into "Day 4 done."

**Decisions made**

- None yet on the UI itself — the fix is Phase 4's job, not an ad hoc patch
  bolted onto Day 4's deliberately minimal scope. Recorded as owner-confirmed
  feedback here so Phase 4 planning starts from a real reaction, not a guess.

**Verification**

- Owner's own live test, mic and all — the one thing this session's automated
  testing structurally could not do itself.
- Re-confirmed the process cleanup with a second `Get-CimInstance` pass after
  force-killing the orphaned Vite child process — empty result, not assumed
  clean from `TaskStop`'s own success message alone.
- No code changed in this entry — nothing to scan for secrets or stage beyond
  this file.
- This entry is being committed on its own, at the owner's explicit request, per
  `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-21 — Phase 3: TEST_PLAN.md Suite C run by voice, 7/7 pass

**What happened**

- Asked to run `TEST_PLAN.md` Suite C (the 7 adversarial questions) "by voice." No
  way to literally speak, and the Browser pane sandbox blocks microphone capture
  (same constraint as Day 4's frontend testing), so the first question was how to
  exercise this honestly rather than skip it or fake it. LiveKit Cloud's Agent
  Console (which has a real text-chat box, used successfully for earlier manual
  testing) turned out to be unreachable too — the Browser pane has no session
  cookie for the owner's LiveKit Cloud account, so `cloud.livekit.io` just showed
  a sign-in page.
- Found a better path by reading the installed SDK rather than giving up: LiveKit
  Agents' `RoomIO` registers a text-stream handler on the `lk.chat` topic by
  default (`TextInputOptions()` is enabled unless explicitly turned off — read
  directly from `livekit/agents/voice/room_io/types.py` and `room_io.py`), and
  the default handler (`_default_text_input_cb`) feeds the text straight into
  `session._claim_user_turn()` — the *same* entry point a real spoken utterance
  uses once STT has produced final text. So driving text into `lk.chat` isn't a
  lesser substitute for a spoken test — for everything Suite C actually checks
  (does the model agree with a false premise, does it guess, does it stay in
  role), it exercises the identical `AgentSession`/`TwinAgent`/tool/LLM code
  path a spoken turn would. STT is the only stage skipped, and Suite C's pass
  criteria never depend on STT accuracy.
- Wrote a standalone script using `livekit.rtc.Room` directly (not the agents
  framework, not the React frontend) to connect as a plain participant with a
  token from the real Token Service, `send_text(question, topic="lk.chat")` for
  each of the 7 questions in turn, with a 14s pace between each — comfortably
  under `gemini-3.5-flash-lite`'s 15 RPM given each grounded turn costs two
  Gemini calls.
- The first run's captured output looked wrong: C4 showed no reply at all, and
  C5 showed two. Rather than report that as-is, cross-checked against the
  worker's own structured log (`turn (user)`/`turn (assistant)`, timestamped) as
  ground truth, and found the real bug: my script's `register_text_stream_handler`
  callback used `asyncio.ensure_future(_read())` — fire-and-forget — so a reply
  that took a while to fully stream (TTS + full-sentence completion) could still
  be in flight when the next question's `send_text` fired, landing the delayed
  reply in the *next* question's capture window instead of its own. The worker's
  log doesn't have this problem — `turn (assistant)` fires once per finalized
  item, correctly ordered relative to the `turn (user)` that preceded it — so
  re-derived every answer from the log instead of trusting the script's own
  capture, and confirmed: 7 questions, 7 real answers, cleanly separated, no
  actual data loss — the bug was in how my script displayed the results, not in
  what the agent said.
- Result: **7/7 pass**, including both tests `TEST_PLAN.md` calls highest-value
  (C1, C4). One worth double-checking rather than taking at face value: C6
  ("what's your biggest weakness?") got refused, and `TEST_PLAN.md` allows either
  "answer from context.md, or refuse" as a pass — but `context.md` does have
  real, relevant content for this exact question (the "what I know deeply versus
  what I've touched once" section, the Mockbuilder failure). Called
  `agent/retrieval.py`'s real `retrieve()` directly with that exact phrasing to
  find out *why* it refused: genuine `no_match` at threshold 0.55. So the
  refusal is the anti-hallucination gate (ADR-004) doing its job correctly for
  this phrasing, not the LLM sitting on content it had and declining to use it —
  a meaningfully different, and better, finding than either possibility looks
  like from the transcript alone.
- Recorded the real results, the methodology note (and its bug), and the C6
  finding directly in `TEST_PLAN.md`'s Suite C table rather than only here, since
  that's the document a future session or the owner's interview prep would
  actually consult for "did Suite C pass."

**Why**

The instinct to treat the first run's garbled output ("C4: no reply") as the
actual finding, rather than a symptom of a bug in the test harness, would have
been a mistake in exactly the direction this project keeps warning against: a
plausible-looking result that isn't actually what happened. Cross-checking
against the worker's own log — the same discipline `CLAUDE.md` rule 2 applies to
reading library source instead of trusting memory — is what turned a confusing,
partially-wrong result into a clean, trustworthy one. The C6 investigation is
the same instinct applied one level up: "it refused" and "it refused correctly"
are different claims, and only checking the actual retrieval result
distinguishes them.

**Decisions made**

- None new — this was a verification pass against existing behavior, not a
  design decision. No code changed.

**Verification**

- Every Suite C answer verified against the worker's own structured, timestamped
  log — not the test script's own (buggy) capture, and not assumed from a
  single read.
- C6's refusal specifically verified by calling the real `retrieve()` function
  directly, not inferred from the LLM's response text.
- Confirmed the token-service/worker pairing used a fresh room (`twin-01f8d4d8`)
  separate from the owner's own manual-test session, so nothing about this run
  could have interfered with or been confused with the owner's earlier test.
- Deleted the temporary test script (`_tmp_suite_c.py`) after use — not
  committed, scratch work only.
- Stopped the Token Service and agent worker processes started for this test,
  and confirmed via `Get-CimInstance` that no orphaned Python processes remained
  afterward.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `f5094e4`, work only — this journal entry is the separate commit
  that follows it, per `CLAUDE.md`'s log-then-commit sequence.

---

## 2026-08-21 — Phase 4: Agent status, mic permission notice, suggested questions

**What happened**

- Added three small components to `web/`, covering three of `BUILD_PLAN.md`
  Phase 4's five prioritized items:
  - `AgentStatus.tsx` — `@livekit/components-react`'s `useVoiceAssistant()` hook
    (already installed at `2.9.24`, no new dependency) exposes the agent
    participant's own state machine directly:
    `disconnected → connecting → pre-connect-buffering → initializing →
    idle/listening/thinking/speaking`, plus a `failed` terminal state. Mapped
    each to a short human label and a colored status dot (idle/listening
    green, thinking/speaking pulsing amber/blue, failed/disconnected red).
    `initializing` gets its own explicit "waking up the agent — this can take
    a few seconds" label rather than reusing "connecting", specifically
    because `DEPLOYMENT.md` Sec4 calls out that exact gap — a visitor staring
    at silence with no indicator during a cold start — as the single most
    common way a working project reads as broken during evaluation. FR-5.2.
  - `MicPermissionNotice.tsx` — explains mic access *before* the visitor
    clicks the toggle ("nothing is recorded until you do"), then listens for
    `RoomEvent.MediaDevicesError` on the room (via `useRoomContext()`) to swap
    in a specific denied-state message pointing at the browser's own
    site-permission UI, rather than a generic failure. Since the `LiveKitRoom`
    `audio` prop was already removed in an earlier session specifically so mic
    access stays opt-in (see this file's 2026-08-21 citations-panel entry),
    this listener only ever fires from an explicit, visitor-initiated request
    — never an automatic one the visitor didn't ask for.
  - `SuggestedQuestions.tsx` — the four `CITATION_SPEC.md` §7 demo questions,
    displayed as read-and-ask-aloud text (this is a voice agent with no text
    input path, so there's nothing to "click to send"). FR-5.4.
- **Swapped the first suggested question.** §7's literal first question,
  "What's your most recent role?", is `TEST_PLAN.md`'s own documented A1
  known gap — confirmed still broken by directly re-running
  `agent.retrieval._match_sync` against the live corpus before touching any
  UI code: it still surfaces three unrelated JobHunt-AI chunks as its top
  results, with the correct Freelance resume chunk absent from the top-4.
  Tested four alternate phrasings the same way; `TEST_PLAN.md`'s own A2
  wording ("What did you work on at your freelance role?") retrieved the
  correct chunk as the clear top-1 result (0.687 similarity vs. the next
  result's 0.631), so that's the phrasing now shown as the first suggested
  question — same underlying demo intent (recent work), a chip that actually
  works. The other three questions are used verbatim from §7.
- Verified the whole thing live, not just built: started the token API, the
  real agent worker (via the correct `python -m livekit.agents start
  agent/main.py` invocation — worth noting since a first attempt using
  `python -m agent.main dev` silently no-op'd and exited immediately, because
  `agent/main.py` has no `__main__` block; that pattern belongs to the
  deprecated `cli.run_app` entrypoint this project explicitly doesn't use, per
  `docs/SDK_NOTES.md`), and the Vite dev server, then loaded the page in a
  real browser. Confirmed via `get_page_text` and a console-error check: the
  agent connected, greeted, and the status pill correctly showed "Speaking…"
  while it did; the mic explainer, all four suggested questions, and the
  empty-state sources panel all rendered with zero console errors.

**Why**

`BUILD_PLAN.md` Phase 4 explicitly ranks connection states as "highest value
... silence with no indicator reads as broken," which is the same principle
`DEPLOYMENT.md` restates for the specific case of a cold start. Doing the
alternate-phrasing check live, the same way the original A1 gap was
discovered (`docs/TEST_PLAN.md`'s 2026-08-21 note), rather than assuming a
rewritten question would obviously work, matched this project's standing
instinct that a plausible-sounding fix and a verified one are not the same
claim.

**Decisions made**

- The first suggested-question chip permanently uses `TEST_PLAN.md`'s A2
  phrasing instead of `CITATION_SPEC.md` §7's literal A1 wording, until the
  underlying retrieval-ranking gap itself is fixed (still open, still
  deferred per `CLAUDE.md`'s current-status tracking) — a UI wording choice,
  not a §7 spec change, so §7 itself is left as written.
- Transcript panel (FR-5.1) and mobile layout (Phase 4 item 6) are not done
  yet — correctly still open, not silently skipped.

**Verification**

- `npm run build` (`tsc -b && vite build`) — clean, zero type errors.
- Live end-to-end run against the real deployed LiveKit Cloud worker (not a
  mock), the real token API, and the real corpus in Supabase — confirmed via
  `get_page_text` and `read_console_messages` (zero errors), not assumed from
  a successful build alone.
- `_match_sync` re-run directly against live retrieval for the original A1
  phrasing (confirmed still broken) and four candidate replacements before
  picking one, rather than trusting the `TEST_PLAN.md` note's age.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `63c9747`, work only.

---

## 2026-08-21 — Phase 5: Token Service deployment prep

**What happened**

- Added `api/requirements.txt`, a minimal, independently-pinned dependency
  list for the Token Service alone: `fastapi`, `uvicorn[standard]`,
  `livekit-api`, `python-dotenv`, `pydantic`. This exists because the
  project's single `pyproject.toml` is shared across `agent/`, `ingestion/`,
  and `api/`, and pulls in `sentence-transformers`/`torch` (100+ MB) for the
  embedding model — none of which the Token Service touches. Deploying the
  Token Service from the full `pyproject.toml` would work, but would make
  every build on the host pull and resolve a dependency tree the service
  never imports, for no benefit. Versions pinned to exactly what
  `uv pip show` reports installed and already verified working locally, not
  guessed.
- Changed `api/config.py`'s `FRONTEND_ORIGIN` (singular, one hardcoded
  string) to `FRONTEND_ORIGINS` (plural, parsed from a comma-separated env
  var) and updated `api/main.py`'s CORS middleware to pass the whole list to
  `allow_origins`. Reasoning: without this, switching the env var to the
  production Vercel origin would break local dev's `localhost:5173` origin,
  and switching back would break production — a single-value config forces
  picking one environment to leave broken at any given time. A
  comma-separated list lets both work simultaneously from one env var.
- Wrote `render.yaml`, a Render Blueprint, so deploying the Token Service is
  "point Render at this repo" rather than manually re-typing the build
  command, start command, and env var names into Render's dashboard by hand
  where a typo silently produces a confusing runtime failure. Specifies the
  free plan, `pip install -r api/requirements.txt` as the build command,
  `uvicorn api.main:app --host 0.0.0.0 --port $PORT` as the start command
  (Render assigns `$PORT` at runtime; hardcoding a port number is a common
  mistake that makes the health check fail), `/health` as the health check
  path, and the four required env vars (`LIVEKIT_URL`, `LIVEKIT_API_KEY`,
  `LIVEKIT_API_SECRET`, `FRONTEND_ORIGIN`) marked `sync: false` so Render
  prompts for each value in its own dashboard rather than storing a default
  or expecting it in the repo.
- Confirmed the GitHub repo (`Pandidharan22/AI-Digital-Twin`) is public via
  an unauthenticated `GET` against the GitHub API (`200`, not `404`) — one of
  `DEPLOYMENT.md`'s pre-submission checklist items, verified now rather than
  assumed, since both Render's and Vercel's GitHub-connected deploy flows
  need it.

**Why**

Deployment topology decisions made under time pressure are exactly the kind
that are easy to get subtly wrong in a way that only surfaces once a real
external host tries to build the project — a slow/bloated build, a CORS
origin that locks out either dev or prod, a hardcoded port that fails a
health check. Working through each of those now, with the actual verified
package versions and the actual `$PORT` mechanism rather than an assumed one,
is the same "run things, don't say this should work" discipline
`CLAUDE.md` states for application code, applied to deployment config before
a host ever sees it.

**Decisions made**

- The Token Service deploys from its own minimal `requirements.txt`, not the
  shared `pyproject.toml`/`uv.lock` — permanent for this service, not a
  temporary shortcut. If its dependencies ever drift from what's actually
  imported in `api/`, `requirements.txt` needs updating by hand; there's no
  automated sync between it and `pyproject.toml`.
- CORS origins are configured as a comma-separated env var permanently, not
  reverted to single-origin once deployment stabilizes.
- The agent worker deploys by running on the owner's own machine for
  tonight's submission rather than to Fly.io, per `docs/DEPLOYMENT.md` Sec2's
  own sanctioned fallback ("runs fine from your laptop for a live demo") —
  Fly.io's account/card verification and first-build time for this project's
  heavy dependency tree were judged too large a risk against tonight's
  deadline. Flagged here as a real, deliberate scope trade, to be revisited
  once there's time to spare, not a permanent architecture decision.

**Verification**

- `uv pip show` cross-checked against every version pinned in
  `api/requirements.txt` — exact match, not approximated.
- Local `curl` against `/health` and `/token` after the CORS change — both
  still return correctly, `access-control-allow-origin` reflecting the
  request's origin.
- `GET https://api.github.com/repos/Pandidharan22/AI-Digital-Twin` →
  `200`, confirming public visibility.
- Scanned the diff for secret-shaped strings before staging — none found
  (`render.yaml`'s env var entries are keys only, `sync: false`, no values).
- Committed as `51a7eb8`, work only.

---

## 2026-08-21 — Phase 5: First live deployment — Render, Vercel, worker

**What happened**

- Deployed the Token Service to Render via the `render.yaml` Blueprint added
  in the previous entry — live at `https://voice-twin-api-46lk.onrender.com`,
  `/health` returning `{"status": "ok"}`.
- Deployed the frontend to Vercel, connected directly to the GitHub repo —
  live at `https://ai-digital-twin-blue.vercel.app`.
- **Found and fixed a real access bug via testing, not assumption.** The
  first Vercel deployment URL obtained (via the GitHub Deployments API's
  `environment_url` field, since the dashboard link the owner had was the
  internal deployment-inspector page, not the public site) returned `HTTP
  302` to `vercel.com/sso-api` on a plain unauthenticated `curl` — Vercel's
  **Deployment Protection** was on, which would have put every visitor
  behind a Vercel login wall, silently defeating the entire point of a
  "hosted link anyone can open." Caught before telling the owner it was
  ready, by actually curling the URL rather than trusting a `200` from the
  Vercel dashboard (which reflects the owner's own authenticated session, not
  what an anonymous visitor sees). Owner disabled Deployment Protection in
  the project's own settings; re-verified with the same unauthenticated
  `curl` afterward — clean `200`, no redirect.
- Wired the two services together by env var, then verified each wiring
  independently rather than trusting the dashboard save:
  - Render's `FRONTEND_ORIGIN` set to the Vercel URL; verified with a `curl
    -X POST /token -H "Origin: <vercel-url>"` showing
    `access-control-allow-origin` echoing back that exact origin.
  - Vercel's `VITE_TOKEN_SERVICE_URL` set to the Render URL and redeployed
    (Vite bakes `VITE_*` vars in at build time — saving the env var alone
    doesn't touch an already-built bundle); verified by fetching the actual
    built JS bundle from the live site and grepping it for the Render
    hostname, confirming `localhost:8000` was not what shipped.
  - Also pushed a one-line fix for Vite's default `web-scaffold-tmp` page
    title, still live on the deployed site until this push — confirmed via
    the same bundle/title fetch method that the redeploy triggered by the
    push actually picked it up.
- **Full cold end-to-end verification**, not just each piece in isolation:
  opened `https://ai-digital-twin-blue.vercel.app` in a browser tab with no
  prior history with the site (the Browser tool's own fresh tab, over the
  real public internet — not `localhost`, not the dev server). Watched the
  agent-status pill go `Connecting…` → `Speaking…` within ~6 seconds, with
  zero browser console errors throughout. That one observed transition is
  proof the entire chain actually works end to end on the real deployed
  infrastructure: the deployed frontend called the deployed Token Service,
  got back a real token, opened a WebRTC connection to LiveKit Cloud, the
  worker (still running as a local process, per the earlier entry's
  documented trade-off — LiveKit dispatch is outbound from the worker, so it
  doesn't matter that it isn't itself "hosted" anywhere) picked up the
  dispatch, joined, and started speaking the greeting.

**Why**

Both real problems this session hit (the SSO wall, the stale bundle) share
the same root cause: the *owner's own browser* — already logged into Vercel,
already having built the page once before — could not have surfaced either
one, because an authenticated session and a cached mental model of "I already
fixed that" both paper over exactly the failure mode a genuinely fresh
visitor would hit. Verifying with unauthenticated `curl` and a browser tab
with no site history isn't paranoia here; it's the only vantage point that
actually matches what `DEPLOYMENT.md`'s "works when someone else clicks it,
cold" requirement is asking for.

**Decisions made**

- No new architecture decisions — this entry is deployment execution and
  verification against decisions already recorded in the prior two entries.

**Verification**

- `curl` (unauthenticated, no browser session) against every URL before
  calling it done: Render `/health` (`200`), the Vercel site root before and
  after disabling Deployment Protection (`302` → `200`), the CORS preflight
  behavior via a direct `POST /token` with an `Origin` header, and the built
  JS bundle's contents for both the API hostname and the page title.
  Nothing in this entry is reported as working from a dashboard screenshot or
  a "should work now" — every claim traces to a command run and its output
  read.
- Live browser verification in a fresh tab against the real public URLs
  (not `localhost`) — `get_page_text` showing the state transition, and
  `read_console_messages` showing zero errors, at both the pre-title-fix and
  post-title-fix points.
- Still open, deliberately not done tonight (see `DEPLOYMENT.md`'s
  pre-submission checklist and Sec4's mandatory cold-start test): the 30-minute-idle-then-cold-open test, moving the worker off the owner's laptop
  to Fly.io, the GitHub Actions ingestion cron, and mobile-Safari/cellular
  verification. Tracked in `CLAUDE.md`'s current-status section, not lost.

---

## 2026-08-21 — Phase 4: Transcript panel (FR-5.1)

**What happened**

- Owner asked for a running text transcript of both sides of the
  conversation, in the same style as LiveKit's own Agent Console/Playground.
  Checked whether `@livekit/components-react` (already installed, `2.9.24`)
  provides this before writing anything custom, per `CLAUDE.md` rule #2's
  general instinct of reading the installed package rather than assuming —
  it does: `useTranscriptions()`, a real exported hook (`components-core`'s
  `TextStreamData[]`). `AgentSession` already publishes both the visitor's
  STT output and the agent's TTS-aligned text as text-stream segments on the
  `lk.transcription` topic automatically — the exact mechanism the Console's
  own transcript view is built on. No agent-side code changed at all; this
  was a frontend-only addition.
- Added `TranscriptPanel.tsx`: sorts the hook's stream data by
  `streamInfo.timestamp`, labels each line "You" or "Twin" by comparing
  `participantInfo.identity` against the local participant's own identity
  (from `useLocalParticipant()`), and auto-scrolls to the latest line.
  React-keyed by `streamInfo.id` — LiveKit assigns one stable id per
  utterance segment and updates the same id's text in place as it grows from
  partial to final, so no manual dedup logic was needed; the hook already
  hands back one current entry per id.
- Wired into `App.tsx` between the `ControlBar` and `SuggestedQuestions`, and
  styled as speaker-colored, right/left-aligned bubbles (visitor right,
  agent left) inside a scrollable, fixed-height container.

**Why**

Checking the installed library before building anything custom mattered
concretely here: a hand-rolled version would have meant either polling
`ChatMessage`/text-stream primitives directly and reimplementing partial-vs-
final segment merging, or (worse) piping the agent's replies through a
second, separate channel that could drift from what was actually spoken.
Using the same hook the Console itself uses guarantees this transcript shows
exactly what LiveKit's own tooling would show for the identical room — no
separate source of truth to keep in sync.

**Decisions made**

- Transcript rendering is entirely client-side, sourced from LiveKit's own
  text-stream primitive — no new backend endpoint, no new data-channel topic,
  and no change to `agent/citations.py` or any other worker code.

**Verification**

- `npm run build` — clean, zero type errors.
- Live run against the real deployed worker (not mocked): watched the
  greeting appear as a single growing line ("Hi, I am Pandidharan Gopiraj's
  voice twin, and") that settled into one complete, non-duplicated final line
  ("...I am glad you are here. Feel free to ask me anything about my
  background and experience.") as the agent-status pill correctly moved
  `Speaking…` → `Listening…` — confirmed via `get_page_text` at two points in
  time, not assumed from the build succeeding.
- `read_console_messages` (errors only) — none, at both checkpoints.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `0867b43`, work only.

---

## 2026-08-21 — Phase 4: UI redesign after first look at the live deployment

**What happened**

- Owner tried the live deployment and pushed back on four specific things,
  each fixed:
  1. **Sources panel took half the screen.** `App.tsx`'s layout was a
     two-column `flex` split (`conversation-panel` / `citations-panel`),
     each `flex: 1`. Replaced with a single centered column
     (`app-shell`, `max-width: 720px`); `CitationsPanel` now renders as a
     compact row directly under the transcript instead of beside it.
  2. **Citation cards dumped the full retrieved excerpt.** `CitationsPanel`
     no longer renders `excerpt` or `score` at all — each source is now a
     small pill showing just `section` + `source`, matching what the owner
     asked for ("Header like 'Education Section - Resume'"). When the
     retrieved chunk carries a `source_url` (GitHub-sourced chunks do;
     resume/`context.md` chunks don't), the chip becomes a real `<a href>`
     instead of plain text — verified both cases render correctly by
     publishing real payloads via `livekit.api.LiveKitAPI().room.send_data`
     directly into the active local room (same technique used earlier in
     Phase 3 Day 4's citations verification), including a `no_match` payload
     to confirm that path still renders as a small "No documented source"
     line rather than nothing.
  3. **Transcript sat in a boxed card that visually fought the page.**
     `TranscriptPanel.tsx` dropped its `<div className="transcript-panel">`
     wrapper (border, background, padding, its own `<h2>`) — the lines now
     flow directly into the page. The bigger part of why it looked "boxy"
     turned out to be `App.css` using hardcoded light-only hex colors
     (`#f4f3ec`, `#ddd`, `#666`, etc.) laid on top of a page that was
     actually rendering in dark mode via `index.css`'s existing
     `--bg`/`--text`/`--border`/`--accent` theme variables (already defined
     for both light and dark there, just never used by `App.css`). Rewrote
     every color in `App.css` to reference those variables instead, so the
     transcript and chips now follow the same theme the rest of the page
     already does automatically.
  4. **Agent-status pill and the mic control were oversized.** The status
     pill's font/padding were cut down and it now sits inline next to the
     mic control instead of stacked full-width. The mic control itself was
     `@livekit/components-react`'s `ControlBar` prefab, which pulls in
     `@livekit/components-styles` and renders a whole toolbar's worth of
     default sizing for what this page only ever needed as one button.
     Replaced with a new `MicToggle.tsx` — a single small pill built
     directly on `useLocalParticipant()`'s `isMicrophoneEnabled` /
     `setMicrophoneEnabled` — and dropped the `components-styles` import
     entirely, now genuinely unused. Cut the shipped CSS bundle from 23.7kB
     to 5.2kB as a direct, measured side effect, not just a visual change.
- Owner asked explicitly not to push this round — committed locally only,
  for them to review against the running local dev server first.

**Why**

The half-screen citations panel and the excerpt dump were both leftovers
from Phase 3 Day 4's citations-panel work, which was explicitly built to
prove the data-channel contract worked (FR-4.6), not to be a finished
design — `BUILD_PLAN.md` Phase 4 was always going to own the real visual
pass, and this session is that pass. The theme-variable fix is worth
noting separately from the others: it wasn't a new color choice, it was
using color tokens that already existed in the codebase (`index.css`,
untouched since the original scaffold) instead of a second, disconnected
set of hardcoded ones `App.css` had been using since Day 4 — the
dark-mode clash the owner saw in their screenshot was that gap made
visible, not a missing feature.

**Decisions made**

- Citation chips permanently omit `excerpt` and `score` from the UI. Both
  fields still travel over the wire in the `citations` payload (unchanged on
  the backend) since they're useful for debugging and could resurface in a
  detail view later, but the default rendering is header-only from here on.
- `ControlBar` and `@livekit/components-styles` are no longer used anywhere
  in `web/` — any future prefab UI from `@livekit/components-react` should
  be re-evaluated against `MicToggle.tsx`'s much smaller custom-component
  approach rather than reflexively reaching for the next prefab.
- Sources render as one compact row per turn, positioned below the whole
  transcript feed rather than interleaved line-by-line under each specific
  agent reply — a deliberate scope cut given the two are separate LiveKit
  primitives on separate topics (`lk.transcription` vs `citations`) with no
  shared ordering guarantee cheap to merge correctly. Flagged as a possible
  future refinement, not implemented tonight.

**Verification**

- `npm run build` — clean, zero type errors; CSS bundle confirmed shrunk
  from 23.7kB to 5.2kB via the build output itself, not estimated.
- Live-reloaded the local dev server against the real running worker and
  Token Service — confirmed the compact status/mic row, the blended
  (unboxed) transcript, and the real spoken greeting all render correctly
  via `get_page_text` and `read_page`, zero console errors.
- Published two real citation payloads (one `match` with a plain-text chip
  and a linked chip, one `no_match`) directly into the live local room via
  `livekit.api.LiveKitAPI().room.send_data(...)` and confirmed via
  `read_page`'s accessibility tree that the GitHub-sourced chip rendered as
  an actual `<a href="https://github.com/...">` element and the plain
  resume-sourced chip did not — not inferred from the payload shape alone.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `c94eb15`, work only, **not pushed** per explicit instruction
  — owner wants to review locally first.

---

## 2026-08-21 — Phase 3/4: "Introduce yourself" retrieval gap, top_k=5, citation doc-type labels

**What happened**

- Owner tried the redesigned UI locally, approved it (pushed `c94eb15` and
  `084b0be`), then flagged a real correctness bug seen live: asking "Can you
  introduce yourself?" got the refusal line — "That is not something I have
  documented" — even though the resume obviously has exactly the right
  content for that question.
- **Diagnosed before fixing**, per `CLAUDE.md`'s working-style rule. Queried
  `agent.retrieval._match_sync` directly for five introduction-style
  phrasings ("introduce yourself", "Can you introduce yourself?", "Tell me
  about yourself", "Who are you", "give me an overview of your background")
  — none of them surfaced the resume's `Objective` section (a genuine
  first-person-style professional summary) in the top results at all; the
  slot kept going to unrelated `Job-Hunt-AI` README chunks instead. Computed
  the actual cosine similarity between each query's embedding and the
  `Objective` chunk's stored embedding directly (fetched via `supabase-py`)
  to rule out a retrieval-pipeline bug: the `Objective` chunk scores
  **0.40–0.47** against every introduction-style phrasing tested, while the
  `Job-Hunt-AI` chunks that won the slot score **0.56–0.59** — both real
  numbers, not estimated. This confirmed the LLM's tool call and the
  no-match refusal logic were both working exactly as designed: it called
  `search_my_background`, got back a real `match` (a `Job-Hunt-AI` doc
  chunk), and correctly declined to answer from it since that chunk isn't
  actually about the owner — the bug is `bge-small-en-v1.5` having weak
  lexical/semantic overlap between meta-conversational phrasing ("introduce
  yourself") and third-person professional-bio text, the same category of
  embedding weakness as the earlier A1 freelance-role gap, just triggered by
  a different query shape.
- Confirmed the fix direction before writing it: a keyword-rich
  reformulation, "AI software engineer objective summary of skills and
  experience," scores **0.822** against the same `Objective` chunk and
  returns it as a clean top-1 (next-closest result 0.786) — an 0.35+ point
  swing from the literal phrasing.
- Added rule 1a to `agent/prompts/system_prompt.md`: for introduction/"who
  are you" style questions, the LLM is told this is still a factual question
  about the owner (the twin *is* the owner), and to call
  `search_my_background` with descriptive resume-language keywords rather
  than echoing the visitor's literal words. Same fix strategy as the earlier
  A1 gap (query-phrasing layer, not the embedding model or the threshold) —
  now applied at the prompt level so the LLM does the rephrasing itself for
  this whole class of question, rather than a single hardcoded UI chip swap
  covering only one specific wording.
- Bumped `RETRIEVAL_TOP_K` 4 → 5 (`.env`, `.env.example`,
  `docs/DEPLOYMENT.md`) per explicit owner request — a ceiling on sources
  shown per turn, not a floor; a turn with only one chunk above threshold
  still shows just one.
- **Citation labeling.** Owner also asked citations to say what kind of
  document a source came from (their example: "Education Section - Resume"),
  not just show the raw section heading, and confirmed the resume case
  should keep showing its section. Queried the live `chunks` table directly
  rather than assuming, and confirmed the ingestion pipeline only ever
  produces three `source_type` values: `resume`, `context`, `github_repo` —
  there's no PRD/SRS/program-file-level distinction to surface yet, since
  `ingestion/loaders/github_loader.py` only ever ingests each repo's
  `README.md` (confirmed by reading the loader directly, not assumed from
  memory). Added `describeSource()` to `CitationsPanel.tsx`: `resume` →
  section heading + "Resume" subtitle; `context` → section heading +
  "Notes (context.md)" subtitle; `github_repo` → strips the redundant
  `"<repo> — "` prefix `_split_readme` bakes into every section heading
  (confirmed live: `"Job-Hunt-AI — Documentation"` → `"Documentation"`) and
  shows `"<repo> — README.md"` as the subtitle, which is an accurate claim
  given today's ingestion scope rather than an overclaim of file-level
  granularity the pipeline doesn't actually have.
- Restarted the local worker process to pick up both the new system prompt
  and the `.env` change — found via `ps -W` that the tool's default PID
  column is a Cygwin-internal id, not the real Windows PID; had to use the
  `WINPID` column (`ps -W -l`) to actually kill the right process after a
  first `taskkill` reported "process not found" against the wrong number.

**Why**

Diagnosing before fixing here mattered because the visible symptom (a
refusal) and the actual defect (a bad retrieval match one layer down) point
in opposite directions — patching the refusal-handling logic would have
been treating the symptom. Computing the real cosine similarity numbers,
not just re-running `_match_sync` and eyeballing which chunk won, is what
turned "the retrieval seems off" into a specific, quantified claim (0.40–0.47
vs. 0.56–0.59, a real gap) that a rephrased query could be tested against
and verified to close.

**Decisions made**

- Introduction-style query rephrasing lives in the system prompt (an LLM
  instruction), not as a special-cased string match in `retrieval.py` or a
  hardcoded UI-only substitution — the earlier A1 fix (swapping the
  suggested-question chip's wording) only helped that one exact chip;
  this fixes the underlying behavior for any phrasing of the same intent
  the LLM chooses to rephrase, both from an actual spoken question and the
  UI's own suggested chip.
- Citation subtitles for `github_repo` sources say "README.md" explicitly
  rather than a vaguer "GitHub" label, since that's the literal, verifiable
  truth of what's ingested today — if ingestion ever expands to pull
  additional files per repo, this label becomes the first thing that needs
  revisiting, not silently stale.

**Verification**

- Real cosine-similarity numbers computed directly against the stored
  `Objective` chunk embedding for both the failing and the fixed query
  phrasings — not inferred from top-4 ranking alone.
- Worker restarted and re-registered with LiveKit Cloud after the prompt/env
  change (confirmed via the `"registered worker"` log line reappearing);
  `_match_sync` re-run post-restart to confirm `RETRIEVAL_TOP_K=5` is live
  (5 results returned where 4 returned before).
- Citation labeling verified live, not just read from the diff: published a
  5-source test payload (2 resume, 1 context, 2 github_repo with real GitHub
  URLs) directly into the running local room via
  `livekit.api.LiveKitAPI().room.send_data(...)`, then read the rendered
  accessibility tree — confirmed all 5 chips rendered, both `github_repo`
  chips had the duplicate repo-name prefix correctly stripped from their
  section label, and both carried real, correct GitHub URLs as links.
- `npm run build` — clean, zero type errors.
- `read_console_messages` (errors only) — none.
- Scanned both diffs for secret-shaped strings before staging — none found.
- Committed as `1ad5eaf` (prompt/config fix) and `10f8a2c` (citation
  labeling), each separate from this journal entry per protocol.

---

## 2026-08-21 — Phase 5: Worker crash — idle job-runner pool sized for a laptop

**What happened**

- Owner reported the local dev page wasn't connecting. Diagnosed rather than
  just restarting blind: checked the worker's own log first, and it showed
  the process had genuinely died — `curl` against its own HTTP port (`8081`)
  returned connection-refused, and no worker process was left running at
  all. The log's last lines before it went silent were a raw
  `MemoryError` raised inside a ctypes callback (`ffi_event_callback`,
  repeated five times) alongside `"job did not ack shutdown in time"` and
  `"job executor is unresponsive"` warnings.
- Restarted it once to see if this was a one-off; it crashed again within
  ~30 seconds, this time with a clean, specific traceback: an `IPC` job
  runner hit `initialize_process_timeout` (10s) while still loading its
  model weights — `TimeoutError` inside
  `livekit/agents/ipc/proc_pool.py:_proc_spawn_task`. Checked system memory
  directly (`Get-CimInstance Win32_OperatingSystem`) rather than guessing:
  free RAM had dropped from ~3.6GB to ~2.2GB between the two crashes, out of
  15.6GB total.
- Found the actual mechanism by reading `AgentServer`'s real constructor
  signature via `inspect.signature()` (not docs, not memory) --
  `num_idle_processes: int | ServerEnvOption[int] = ServerEnvOption(dev_default=0, prod_default=12)`.
  This worker has to run via the `start` command for real room dispatch to
  work at all (`console` mode's lower dev default doesn't apply --
  `docs/SDK_NOTES.md` already established `start` as the only correct
  invocation back in Phase 1), which means it was defaulting to **12** idle
  processes kept warm at all times, each one independently loading
  `torch` + `bge-small-en-v1.5` + `onnxruntime` for `agent/main.py`'s own
  `_prewarm` hook. Twelve concurrent model loads against ~2-3GB of
  actually-free RAM (this machine, tonight, with everything else already
  running) is what crashed the process outright -- not a code bug, a
  resource-sizing default tuned for real server hardware, silently wrong
  for a laptop.
- Added `agent/config.py`'s `WORKER_NUM_IDLE_PROCESSES` (env-overridable,
  defaults to `2`) and passed it into `AgentServer(...)` in
  `agent/main.py`. Also caught and fixed a small inconsistency while in
  `config.py`: `RETRIEVAL_TOP_K`'s Python-level fallback default was still
  `4`, one commit behind `.env`/`.env.example`'s already-bumped `5` — a
  clone without the env var explicitly set would have silently diverged
  from the documented default.
- Restarted the worker a third time with the fix. Registered cleanly in
  under 9 seconds (down from crashing before it ever finished), and picked
  up a real room dispatch from the already-open local dev tab immediately
  afterward. Reopened the browser preview (the session had dropped when the
  worker died) and watched the agent-status pill move
  `Connecting…` → `Speaking…` with the real greeting text, zero console
  errors.

**Why**

Reading the actual crash log and checking real memory numbers before
touching anything mattered here because the fix could easily have gone
wrong in either direction: patching `_prewarm` to load the model lazily
instead would have reintroduced the exact 13.79s per-turn latency spike
that hook was built to eliminate in Phase 3 (see this file's earlier
`_prewarm` entry), while blindly restarting on a loop would have kept
crashing at the same resource ceiling. Reading `AgentServer`'s real
constructor signature is the same "verify the installed package, don't
assume the API" habit `CLAUDE.md` rule #2 has held since Phase 0 --
`num_idle_processes` having a *different* default in dev vs. prod mode
isn't something a general LiveKit tutorial would call out, since it only
bites when `start` mode's higher default meets a resource-constrained host,
which is exactly tonight's situation.

**Decisions made**

- `WORKER_NUM_IDLE_PROCESSES` defaults to `2` for now -- enough headroom for
  one local visitor without repeating tonight's crash. Explicitly flagged in
  both the code comment and `.env.example` as a value to raise once the
  worker runs on real server hardware (Fly.io) instead of this laptop,
  rather than left as an unexplained magic number.
- Kept `_prewarm`'s eager-load-at-startup behavior unchanged -- the fix is
  sizing the pool, not removing the optimization that pool exists to serve.

**Verification**

- Root cause confirmed from two independent, real signals: the process's own
  exception traceback (not inferred from symptoms) and actual
  `Get-CimInstance`-reported free memory before and after the second crash,
  not assumed from "it's probably low on RAM."
- `inspect.signature(AgentServer.__init__)` run directly against the
  installed `livekit-agents==1.6.10` to confirm the real default value and
  parameter name, rather than trusting recalled API shape.
- Live restart verification: worker registered in ~9s (previously crashed
  before completing registration), picked up a real dispatch, and the
  browser showed the full `Connecting…` → `Speaking…` transition, greeting
  text, and zero console errors -- checked via `get_page_text` and
  `read_console_messages`, not assumed from the log alone.
- Scanned the diff for secret-shaped strings before staging — none found.
- Committed as `5425038`, work only.

---

## 2026-08-21/22 — Phase 5: Worker moved off the laptop, onto Fly.io

**What happened**

Owner asked to close out the last major deferred item from the deployment
sprint: move the agent worker off this machine and onto Fly.io, per
`docs/DEPLOYMENT.md`'s original recommendation. Installed `flyctl` (a plain
CLI download, not an account action) and Docker Desktop was already present
but needed starting. Fly.io itself needed a real account with a card on
file — owner created it and ran `flyctl auth login` themselves; verified
from this session via `flyctl auth whoami`.

**Four real, distinct problems found and fixed, each via evidence, not
assumption:**

1. **`uv sync` on Linux pulled the full CUDA torch stack.** A first local
   Docker build attempt hit 5.5GB and failed on a flaky download partway
   through. Read the actual layer-by-layer build output rather than
   guessing: `nvidia-cublas` (403MB), `nvidia-cudnn` (349MB),
   `nvidia-cusolver` (191MB), `cuda-toolkit`, `triton` — 2.5GB+ of pure GPU
   dependencies this CPU-only project never touches. Fixed with
   `[tool.uv.sources]`/`[[tool.uv.index]]` pinning torch to
   `download.pytorch.org/whl/cpu` in `pyproject.toml` — but this didn't
   work on the first two attempts (`uv lock -v` kept showing
   `pypi.org/simple/torch/` as the resolved source despite the pin). Root
   cause: torch was only a *transitive* dependency (via
   `sentence-transformers`), and uv's source override doesn't reliably bind
   to purely-transitive packages in this uv version. Making torch an
   explicit direct dependency fixed it immediately — package count dropped
   152 → 134, every `nvidia-*`/`cuda-toolkit`/`triton` entry gone. Verified
   locally first (`torch.__version__` now reports `2.13.0+cpu`, embedder
   still returns a real 384-dim vector) before ever touching the Docker
   build again.
2. **Fly's `bom` (Mumbai) region is deprecated for new resources.** First
   deploy attempt failed outright at machine-creation with an explicit
   error naming `sin` (Singapore) as the suggested alternative — a clean,
   actionable error, not a mystery. Switched `fly.toml`'s `primary_region`.
3. **`shared-cpu-2x` genuinely couldn't keep up under concurrent load.**
   Even after the image built cleanly (432MB, confirming the torch fix),
   the deployed worker got stuck in an endless kill-and-retry loop:
   `initialize_process_timeout` (10s default) kept expiring mid-import,
   `"worker is at full capacity"` fired at `load=1.3` against a `0.7`
   threshold. Two stale browser tabs left open from earlier testing were
   both triggering simultaneous cold dispatches, doubling the real
   contention — closed them before continuing, to stop testing against a
   self-inflicted worst case. Raised `initialize_process_timeout` to 30s
   first (cheap to try) via a new `WORKER_INITIALIZE_TIMEOUT` config value —
   it still timed out, proving this wasn't just "needs a bigger number."
   Escalated to `performance-2x`/4GB (dedicated vCPUs, not shared/throttled)
   as the more expensive but more honest fix.
4. **The actual dominant cost was never CPU at all.** Even on dedicated
   CPU, cold starts were still slow and intermittently timing out. Read the
   log timeline closely instead of assuming the CPU upgrade alone would
   fix it: `SentenceTransformer(...)`'s constructor was hitting Hugging
   Face Hub over the network on *every* cold job-runner start —
   `"unauthenticated requests to the HF Hub"` on every single init, and a
   measured ~19-second gap between "loading model" and "loading weights"
   that had nothing to do with the weights themselves (which load in under
   a second once local). This is a variant of the exact same class of bug
   Phase 3's `_prewarm` hook was built to solve for the in-process case —
   just one layer further out, at the per-subprocess Docker cold-start
   layer, where `_prewarm`'s in-memory warm cache doesn't reach. Fixed
   properly: baked the model into `agent/Dockerfile` at build time
   (`SentenceTransformer('BAAI/bge-small-en-v1.5')` as a `RUN` step, same
   pattern already used for Silero VAD via `download-files`) and set
   `HF_HUB_OFFLINE=1` so runtime never re-attempts the network call at all.
   Real init time dropped to ~20s, well inside the 30s timeout, with zero
   HF Hub warnings in the logs afterward — confirmed on a live redeploy,
   not assumed from the fix's plausibility.
- Removed the now-genuinely-redundant `uv pip install torch --index-url
  ...` line the Dockerfile had carried since problem #1's *first* (wrong)
  fix attempt — the lockfile pin makes it a guaranteed no-op now.
  Redeployed once more after removing it specifically to confirm no
  regression, rather than assuming a cleanup commit is risk-free.
- Final live end-to-end verification, same standard as the original
  deployment entry: opened the real production URL
  (`https://ai-digital-twin-blue.vercel.app`) in a fresh browser tab,
  watched `Connecting…` → `Speaking…`, read the actual greeting text, zero
  console errors — and confirmed via `flyctl logs` that this was genuinely
  served by the Fly.io worker (`region: "India South"` LiveKit-side,
  `region: sin` Fly-side), not a leftover local process (which was
  deliberately stopped and confirmed dead via `curl` against `:8081`
  returning connection-refused).

**Why**

Every one of these four problems looked, at first glance, like it could be
explained by the previous one's fix not being "enough" — more memory, more
CPU, a longer timeout. The discipline that actually closed each one was the
same throughout: read the real log line, the real timestamp gap, the real
resolved dependency source, before reaching for the next lever. Problem #4
in particular would have been easy to mis-diagnose forever as "needs an
even bigger VM" if the ~19-second gap between two specific log lines hadn't
been read closely enough to notice it was a network wait, not compute.

**Decisions made**

- Worker VM sized at `performance-2x`/4GB (dedicated CPU) permanently, not
  `shared-cpu-2x` — this has real ongoing Fly.io billing cost, unlike the
  free-tier-first stance the rest of this project has held; flagged
  explicitly rather than left implicit, since it's a genuine scope
  exception to `CLAUDE.md`'s "everything free tier" framing, matching
  `DEPLOYMENT.md`'s own "a few dollars to avoid failing evaluation is
  rational" guidance.
- `HF_HUB_OFFLINE=1` is now a permanent runtime setting for the worker
  image — baked into the Dockerfile itself, not left as a Fly secret,
  since it's a build-time-coupled decision (the model has to already be in
  the image for offline mode to work at all).
- The local-laptop worker process is fully retired, not kept as a fallback
  — `docs/DEPLOYMENT.md` Sec7's own contingency table still lists "run the
  worker locally" as the demo-day fallback if the hosted worker dies, so
  this isn't lost, just no longer the primary path.

**Verification**

- Every fix in this entry was confirmed against a real redeploy and real
  log output, not inferred from the fix's own plausibility — including the
  two attempts that *didn't* work (the first two torch source-pin tries,
  the 30s-timeout-alone try), which are recorded here specifically because
  a journal that only shows the fix that worked hides the actual debugging
  path.
- Final state confirmed via `flyctl status` (machine `started`, dedicated
  CPU, 4096MB), `flyctl logs` (clean `registered worker`, no timeout, no HF
  Hub warning), and a live browser session against the real production URL
  showing a full greeting with zero console errors.
- Scanned every diff for secret-shaped strings before staging — none found;
  Fly secrets were set via `flyctl secrets import` reading from a temp file
  that was deleted immediately after, never echoed into any tool output.
- Committed as `dd79f08` (torch CPU pin), `d151998` (Dockerfile + fly.toml),
  `1f12dac` (Dockerfile cleanup), `935c771` (timeout config) — each a
  separate work commit per protocol.

---

## 2026-08-22 — Phase 5: Fly.io VM downgrade — dedicated CPU wasn't the fix

**What happened**

- Owner asked directly whether Fly.io actually bills, having only added a
  card during account creation without seeing a price anywhere. Checked
  Fly's real pricing docs live (`fly.io/docs/about/pricing/`) rather than
  answer from memory or reassure without checking: **no free tier**, a card
  on file is required for every account, billing is per-second, and
  `performance-2x`/4GB was running ~$60–70/month continuously — a real,
  ongoing cost that should have been priced out *before* deploying it, not
  discovered after.
- Owner asked to combine two mitigations: downgrade to a cheaper VM class,
  and add auto-stop-when-idle. Checked Fly's own autostop/autostart docs
  before configuring anything, rather than writing a `fly.toml` block that
  might silently not work: **autostop requires an `[http_service]` block**
  so Fly's proxy has traffic to watch. This worker has none by design (it's
  outbound-only, connects to LiveKit Cloud, never accepts inbound
  connections — see the original Dockerfile/fly.toml entry) — there is
  nothing for Fly's proxy-based autostop to gate on, and building a custom
  idle-exit would mean the worker is unregistered (and so undispatchable)
  exactly while "waiting to be needed," reintroducing the same
  nobody-joins-the-room failure mode Phase 5 already spent a full session
  fixing. Reported this limitation honestly instead of configuring
  something that would have looked correct in `fly.toml` but done nothing.
- The downgrade half was worth retesting for a real reason, not just cost:
  every prior `shared-cpu-2x` failure in this file's own history happened
  *before* the actual root cause (the Hugging Face Hub network call) was
  fixed. The escalation to `performance-2x` happened mid-debugging, before
  that fix landed — so dedicated CPU was never actually proven necessary on
  its own merits, just correlated with the moment things started working.
  Downgraded `fly.toml` back to `shared-cpu-2x`/2GB and redeployed to find
  out for real.
- **Confirmed live: shared CPU works fine now.** `process initialized` at
  21.53s — statistically the same as dedicated CPU's ~20s, well inside the
  30s timeout, zero errors, zero HF Hub warnings. Re-verified end-to-end
  through the real production URL (`Connecting…` → `Speaking…`, real
  greeting text, zero console errors) before calling it done.
- Looked up real `shared-cpu-2x`/2GB pricing the same way (Fly's docs, not
  memory): roughly $11–15/month continuous, vs. `performance-2x`/4GB's
  $60–70/month — a 5–6x cost cut for identical observed reliability.
- Since true idle autostop isn't available, gave the owner the honest
  fallback instead: `flyctl scale count 0` / `scale count 1` as a manual
  stop-before/start-before-a-session toggle — zero cost while stopped, ~20s
  to register again before it can take a visitor.

**Why**

Both parts of this entry are the same lesson from opposite directions: the
first (checking real pricing before answering "does it bill me") is
verifying a claim about money before making it, the same standard `CLAUDE.md`
holds for technical claims. The second (checking Fly's actual autostop
mechanics before configuring it) is the inverse mistake avoided —
implementing something that *looks* like it solves the ask without
confirming it actually would have, which would have been worse than
reporting the limitation, since a `fly.toml` block that quietly does
nothing reads as "handled" until the next bill arrives.

**Decisions made**

- `shared-cpu-2x`/2GB is the worker's VM size going forward, not
  `performance-2x` — the earlier entry's "this has real ongoing billing
  cost" framing is now `docs/DEV_JOURNAL.md`'s own outdated 2026-08-21
  reasoning superseded by same-day retesting, not erased, per this
  journal's own standing convention of annotating reversed decisions rather
  than rewriting history.
- No automatic idle-stop is configured or planned for this worker shape.
  Documented as a real architectural limitation (no inbound traffic for
  Fly's proxy to watch), not a TODO — a genuine fix would require
  application-level self-management that trades away exactly the
  reliability Phase 5 was built around.

**Verification**

- Fly's real pricing and autostop documentation fetched and read directly
  (`fly.io/docs/about/pricing/`, `fly.io/docs/launch/autostop-autostart/`)
  before making any claim to the owner about cost or configuring any new
  `fly.toml` behavior — not answered from training-data recall of Fly's
  pricing model, which changes over time.
- Live redeploy on `shared-cpu-2x`/2GB: `flyctl logs` showing
  `process initialized` in 21.53s with zero errors, then a full browser
  session against the real production URL confirming `Connecting…` →
  `Speaking…` with the actual greeting text and zero console errors.
- Scanned the diff for secret-shaped strings before staging — none found
  (a one-line VM-size/memory change).
- Committed as `79a31da`, work only.

---

## 2026-08-22 — Phase 5: live outage, `shared-cpu-2x` reverted, Render cold-start fixed

**What happened**

Owner reported the production site stuck on "Connecting…" shortly after the
`shared-cpu-2x` downgrade above. Two genuinely separate problems, diagnosed
in order rather than assumed to be the same one:

1. **`shared-cpu-2x` regressed on its own.** `flyctl logs` showed the exact
   same kill-and-retry `TimeoutError` loop from before the CPU-class
   escalation, now happening again on the *same* VM class that had tested
   clean just hours earlier. This is the honest failure mode of "shared"
   CPU: performance depends on whatever else is running on the same
   physical host at that moment, so one passing test is a sample, not a
   proof. The earlier entry's "confirmed live" language oversold a single
   data point. Reverted to `performance-2x`/4GB immediately — this was a
   live outage, not a background improvement, so it shipped before writing
   this entry, not after. Redeployed, confirmed `process initialized` in
   ~21s with zero errors, verified via a fresh browser session against the
   real production URL. `shared-cpu-2x` is not reused for this worker going
   forward; `fly.toml` stays on `performance-2x`.
2. **Separately, Render's token API had spun down.** With the Fly issue
   fixed, the frontend was *still* stuck — this time because the free-tier
   Render service goes to sleep after ~15 min with no inbound traffic, and
   the first request after that pays a real cold-start cost. Watched it
   directly: repeated 503s, then an "Application loading" placeholder, then
   a successful response after roughly 60-90s total — worse than
   `docs/DEPLOYMENT.md`'s own "10-30s" estimate for this exact scenario,
   worth knowing for next time.
3. **A third, separate signal surfaced during diagnosis and was correctly
   set aside.** Testing from this session's own Bash tool, DNS lookups for
   `onrender.com` returned obviously-wrong IPs — even when the resolver was
   explicitly pointed at `8.8.8.8`, and even via DNS-over-HTTPS to bypass
   local interception for a sanity check (which returned Render's real,
   correct IP). A direct connection to that real IP then hung for a full
   60s with no response, consistent with SNI-based filtering somewhere on
   the owner's local network (router-level DNS filtering, ISP hijacking, or
   security software), not a Render-side problem. Confirmed this was
   local-network-specific, not universal, by reaching Render fine from a
   separate browser sandbox on a different network. Reported to the owner
   as something outside this session's reach to fix (no tool access to
   their router/ISP), rather than either ignoring it or spending further
   session time on a problem this agent cannot act on.

**Then, the actual fix for problem #2:** built the keep-warm ping
`docs/DEPLOYMENT.md` Sec4 had already specified but never implemented
(`GET /health` every 5-10 min) — `.github/workflows/keep-warm.yml`, a
`schedule: cron` GitHub Actions workflow hitting the token API's existing
`/health` endpoint (already present in `api/main.py`, already commented
"also the keep-warm ping target" — this was designed for from the start,
just never wired up). Chose GitHub Actions over an external uptime pinger
(the doc's other listed option) since Actions is already this project's
mechanism for the ingestion cron — no new account, no new secret, `/health`
is a public unauthenticated GET.

**Why**

The manual-trigger verification step matters more than it looks: this
session's own ingestion PAT lacks `actions:write` scope, and rather than
widen that token's permissions just to self-verify, the honest move was to
ask the owner to click "Run workflow" once. Widening a token's scope beyond
what its original purpose needed, even temporarily, is exactly the kind of
small permission-creep that's easy to justify in the moment and easy to
regret later — not doing it here even though it would have saved one
back-and-forth.

**Decisions made**

- `performance-2x`/4GB is the worker's VM size again, and this time framed
  as the *actually* settled choice, with the prior entry's "confirmed
  shared CPU works" superseded in place by this one rather than deleted —
  same annotate-don't-rewrite convention as always. The real lesson: a
  single successful load test on a "shared" resource class is not evidence
  of reliability, only evidence it can work.
- Keep-warm ping lives in `.github/workflows/keep-warm.yml`, cron
  `*/10 * * * *`, `workflow_dispatch` also enabled for manual runs.
- The local-DNS-interference finding is the owner's to act on (router/ISP
  settings), not something fixed in this repo — noted here so a future
  session doesn't waste time re-diagnosing it from scratch if it resurfaces.

**Verification**

- Root cause of the Fly regression confirmed from the same
  `TimeoutError`/kill-loop signature as the original diagnosis, not
  guessed — then fixed and reverified with a live redeploy and a real
  browser session, not assumed from the fix's plausibility.
- Render cold-start timing observed directly (503s, then "Application
  loading", then success), not estimated from the docs.
- DNS hijacking finding cross-checked three ways before being reported as
  fact: local resolver, explicit `8.8.8.8` query (same wrong answer,
  confirming interception isn't resolver-specific), and DNS-over-HTTPS
  (correct answer, confirming the real record is fine) — then confirmed
  network-specific, not universal, via a working fetch from an unrelated
  browser sandbox.
- Keep-warm workflow verified two ways: local `yaml.safe_load` before
  committing, then a real `workflow_dispatch` run after push, confirmed via
  the GitHub API showing `"status": "completed", "conclusion": "success"`
  — not assumed working just because the YAML was syntactically valid and
  GitHub listed it as "active".
- Scanned every diff for secret-shaped strings before staging — none found.
- Committed as `8b0aa61` (fly.toml revert to `performance-2x`) and
  `f588159` (`.github/workflows/keep-warm.yml`) — each a separate work
  commit per protocol.

**Same-day addendum: the keep-warm workflow itself needed a fix.** Owner
reported a run had failed shortly after the entry above was written. Pulled
the actual run logs (`.../actions/runs/{id}/logs`) rather than guessing —
`curl: (28) Operation timed out after 30002 milliseconds`. Checked the
surrounding runs' timestamps and found the real cause: GitHub's `schedule`
trigger doesn't fire at exact 10-minute intervals (documented, not a bug
here) — two runs that day landed after a 25-31 min gap instead of 10, long
enough for Render to have gone back to sleep in between. That turned those
particular pings into genuine cold-start requests, which had measured
60-90s live earlier that same night — well past the original 30s
`--max-time`. The pings that failed were exactly the ones that mattered
most: the ones actually needed to wake a sleeping instance back up, not
routine keep-warm touches on an already-warm one.

Fixed by raising the per-attempt timeout to 100s and adding an explicit
two-attempt bash loop, deliberately not curl's own `--retry` — its
interaction with `--max-time` (whether the time budget is per-attempt or
shared across all retries) wasn't something to guess at for a step whose
only job is not silently failing. Verified live: a new scheduled run fired
naturally after the fix was pushed and succeeded, without needing a manual
`workflow_dispatch` to confirm it.

**Verification (addendum):** diagnosed from the actual downloaded run logs,
not inferred from the failure conclusion alone; fix confirmed via a real
subsequent scheduled run's `conclusion: success`, not assumed from the
YAML being valid. Committed as `c353247`, work only.

---

## 2026-08-22 — Post-launch hardening: to-do list, and the first real LLM latency measurement

**What happened**

With Phases 0–5 substantially built and live, this entry starts a new pass
focused on production-standard hardening rather than new phases: read the
full documentation set, `agent/*.py`, `api/main.py`, and the frontend cold,
compiled a to-do list of everything still open (the retrieval-ranking gap on
Suite A1, mobile responsive layout, `POST /token` rate limiting, an
automated retrieval/citation test suite, the still-unmeasured 20-turn
latency baseline, and the remaining Phase 5/6 checklist items), and started
with the latency measurement — the item Phase 1 had flagged with real but
stale numbers (2.5s avg TTFT measured against a trivial no-persona prompt,
long before Phase 3's real system prompt and tool-calling existed).

- Built `tests/measure_latency.py`: connects to LiveKit as a plain
  `rtc.Room` client (reusing `api.main.create_token()` directly rather than
  re-implementing token minting), drives 20 realistic questions — a mix
  drawn from `TEST_PLAN.md` Suites A/B/C, including A1's own known
  ranking-gap question — into the room over the `lk.chat` text-stream
  topic, paced 14s apart. Same substitution `TEST_PLAN.md` Suite C used
  and for the same reason: this environment's Browser pane sandbox can't
  capture a real microphone, and `lk.chat` text feeds into the identical
  `_claim_user_turn()` entry point a spoken utterance reaches after STT —
  confirmed again directly from `livekit/agents/voice/room_io/room_io.py`
  and `types.py`, not assumed to still be true since the last time this was
  checked.
- Built `tests/parse_latency_log.py`: reads `flyctl logs` output (or a
  local `worker.log`-style capture), strips the ANSI-colored
  `<timestamp> app[id] region [level]` prefix `flyctl` adds ahead of each
  JSON payload, parses the JSON, regexes `agent/main.py`'s own
  `"turn metrics: transcription_delay=... end_of_turn_delay=... llm_ttft=...
  tts_ttfb=... e2e_latency=..."` log message (already emitted on every
  turn since Phase 1 — no agent code changed for this), and reports
  median/p95 per stage, dropping `None` values per-field rather than
  treating them as zero.
- **Ran it for real against the live production Fly.io worker** —
  deliberately not against a second local worker instance, specifically to
  avoid a second process registering for automatic dispatch alongside the
  one real visitors could be routed to. Captured `flyctl logs -a
  voice-twin-worker` to a file for the run's duration, then parsed just
  that run's room (`twin-12e72214`) out of the (much larger, multi-room)
  capture.
- **Real finding:** all 21 assistant turns (greeting + 20 replies) reported
  `llm_ttft` and `tts_ttfb` — full coverage, no dropped turns. Median
  `llm_ttft` **1066ms**, p95 **1276ms** (min 857ms, max 1635ms — a tight
  distribution, not one unlucky outlier). Median `tts_ttfb` 244ms, p95
  326ms. Recorded directly in `TEST_PLAN.md` Sec3.
- **Equally real, and reported rather than glossed over: `e2e_latency`,
  `transcription_delay`, and `end_of_turn_delay` were `None` on every
  single one of the 21 turns.** Not a parser bug — checked the raw parsed
  fields directly before concluding this. `ChatMessage.metrics.e2e_latency`
  is anchored to the STT/VAD-driven end-of-utterance event, and literal
  text injected into `lk.chat` never fires that event — there's no
  "utterance" to end. So this run answers "how fast does the LLM+TTS half
  of the pipeline respond" honestly and with a real sample size, but
  cannot answer TEST_PLAN.md's Total (median/p95) or STT rows at all — a
  genuine method boundary, documented in `TEST_PLAN.md` rather than left
  implicit, with a real voice pass (a person actually speaking through the
  frontend) named as the specific way to close it.
- Also confirmed, while writing up the method note: `agent/retrieval.py`
  and `agent/main.py` don't separately time the retrieval stage anywhere —
  its own `<100ms` target is currently unverifiable without adding a
  dedicated timer around `retrieval.retrieve()`, folded invisibly into
  `llm_ttft` from the caller's perspective today. Flagged as open, not
  fixed here — this entry is a measurement pass, not an optimization pass.

**Why**

Phase 1's latency numbers were real when they were taken, but they were
measured against a placeholder prompt with no retrieval, no tool-calling,
and an earlier LLM choice — carrying them forward into a "production
standard" pass would have meant optimizing against a number that no longer
describes the actual system. Running a full 20-turn suite against the real
deployed worker, with the real system prompt and the real question mix
(including known-difficult ones like A1 and the salary anomaly), is the
same "run it for real, don't assume" standard this project has held since
Phase 0 — applied here to its own earlier findings, not just to new code.
Running against the live Fly.io worker instead of a second local instance
mattered specifically because LiveKit dispatch has no built-in preference
between two registered workers for the same project; spinning up a second
one, even briefly, risked a real visitor's room landing on the throwaway
instance instead of the stable one.

**Decisions made**

- `tests/measure_latency.py` and `tests/parse_latency_log.py` are now
  permanent, reusable tools, not one-off scripts — re-running the latency
  suite after any future prompt or model change is now a two-command
  operation instead of a bespoke script written from scratch each time.
- The Total/STT gap is explicitly left open rather than worked around with
  a synthetic audio track or similar — a real voice pass answers it more
  honestly than a simulated one would, and this was a measurement task, not
  where that engineering effort belonged.
- Retrieval-stage timing is now a named, specific follow-up (add a timer in
  `retrieval.retrieve()`), not a vague "latency might be an issue" note.

**Verification**

- `uv run python -m py_compile` on both new scripts before running either
  for real.
- Parser sanity-checked against a real, already-existing `flyctl logs`
  sample (a different, earlier room from casual prior testing) before
  trusting it against the actual measurement run — caught and fixed the
  ANSI-prefix-vs-plain-JSON assumption this way, before it could have
  silently produced an empty report against the real run.
- The real run's own console output (20/20 questions sent, clean connect/
  disconnect, no errors) cross-checked against the parsed line count (21
  matched turn-metrics lines against 21 expected turns) — confirms nothing
  was silently dropped between the two tool runs.
- Scanned `tests/measure_latency.py`, `tests/parse_latency_log.py`, and the
  `TEST_PLAN.md` diff for secret-shaped strings before staging — none
  found.
- `git status --short` after staging → exactly the three intended files.
- Committed as `ffbcd95`, work only, separate from this journal entry.
- No deploy involved and none needed — this added local tooling and a docs
  update; nothing in `agent/`, `api/`, or `web/` changed, so the currently
  running production worker and frontend are unaffected either way.
