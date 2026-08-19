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

## 2026-08-18 — Phase 2: Planning the pipeline; GitHub REST vs. MCP client decision

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

## 2026-08-18 — Phase 2: Ingestion dependencies

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

## 2026-08-18 — Phase 2: Supabase schema — chunks table and match_chunks RPC

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

## 2026-08-18 — Phase 2: PDF loader — resume, tuned to its real extracted structure

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

## 2026-08-18 — Phase 2: Markdown loader for context.md

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
