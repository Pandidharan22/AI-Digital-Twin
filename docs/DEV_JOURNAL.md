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

Newest entries are at the top.

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
  which exists for the same fast-orientation reason).
- One entry generally corresponds to one work commit, cross-referenced by short hash,
  so the journal can be used to walk the commit history narratively.

**Verification**

- `git diff` reviewed line-by-line before staging — confirmed the addition was purely
  additive (15 insertions, 0 deletions across both files).
- `git status` after commit → working tree clean apart from the not-yet-committed
  journal file itself.

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
