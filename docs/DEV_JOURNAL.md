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
