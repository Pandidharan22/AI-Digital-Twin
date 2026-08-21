# CLAUDE.md — Voice Twin

> **Place this file in the PROJECT ROOT, not in `docs/`.** Claude Code reads it
> automatically at the start of every session. It is what keeps the agent on-spec
> across many sessions.

---

## What this project is

A real-time voice agent that answers questions about **[YOUR NAME]** using LiveKit,
grounded in a curated corpus of their own documents, where **every factual claim is
traceable to a source displayed in the UI**.

Built for a hiring evaluation. The bar is a working, hosted, polished product — not a
prototype.

---

## Non-negotiable rules

1. **Never hardcode secrets.** Everything through environment variables. `.env` is
   gitignored. Check before every commit.

2. **Verify the LiveKit SDK before writing pipeline code.** The Agents framework
   changed significantly in 1.0 — `AgentSession` replaced `VoicePipelineAgent`. Read
   the installed package's actual API surface. Do not reproduce patterns from memory or
   from older tutorials. `docs/SDK_NOTES.md` holds verified findings.

3. **Citations come from the retrieval layer, never from the LLM.** The LLM must not
   generate citation text. The worker publishes what was actually retrieved. See
   ADR-005.

4. **Publish citations BEFORE the LLM generates**, so source cards render before speech
   begins.

5. **The threshold gate is the anti-hallucination mechanism.** Retrieval below
   threshold returns `no_match` with an empty result set. Prompts alone are not
   sufficient — see `docs/CITATION_SPEC.md` §2.

6. **No LinkedIn scraping.** Ever. Official data export only. Community LinkedIn MCP
   servers violate LinkedIn's terms. See ADR-003.

7. **Bot output must be plain speakable text.** No markdown, asterisks, bullets, or
   emoji — TTS reads them aloud.

8. **Retrieval is offline-indexed, queried at runtime.** Never fetch from live APIs on
   the request path — it blows the latency budget. MCP belongs in ingestion. See ADR-002.

---

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Transport | LiveKit Cloud | Free Build plan |
| STT | Deepgram Nova-3 | Streaming; $200 free credit |
| LLM | Gemini Flash | Free tier; 5 RPM (`gemini-3.7-flash`, verified live 2026-08-20) — handle 429s |
| TTS | Deepgram Aura-2 | **Same credit as STT** |
| Embeddings | `bge-small-en-v1.5` local | CPU, 384 dims |
| Vector store | Supabase pgvector | Free tier |
| Backend | Python 3.11+, FastAPI | `uv` for deps |
| Frontend | React + LiveKit components | Vercel |
| Freshness | Official GitHub MCP | Ingestion only |

Everything is free tier. Do not introduce paid dependencies without asking.

---

## Architecture in one paragraph

Browser connects to a LiveKit room using a token from the FastAPI service. A Python
agent worker joins the same room, runs Deepgram STT → Gemini Flash → Deepgram TTS. The
LLM has one primary tool, `search_my_background`, which does threshold-gated pgvector
similarity search. Retrieved sources are published to the data channel before the LLM
generates, so the UI shows the citation before the claim is spoken. An offline
ingestion job — GitHub via official MCP, plus local documents — keeps the corpus fresh.

---

## Key files

| Path | Purpose |
|---|---|
| `agent/main.py` | Worker entrypoint, session wiring |
| `agent/twin_agent.py` | Agent subclass, instructions, tools |
| `agent/retrieval.py` | pgvector search + threshold gate |
| `agent/citations.py` | Data channel publishing |
| `agent/prompts/system_prompt.md` | Grounding contract — editable, not in code |
| `ingestion/ingest.py` | Corpus pipeline orchestrator |
| `api/main.py` | Token service |
| `docs/` | Full specification set |
| `docs/DEV_JOURNAL.md` | Dated log of every verified step — decisions, changes, removals; written for interview prep |

---

## Documentation map

Read the relevant doc **before** implementing:

- `docs/SRS.md` — numbered requirements; cite IDs when implementing
- `docs/CITATION_SPEC.md` — the citation contract; **most important doc**
- `docs/ARCHITECTURE.md` — design decisions and rationale (ADRs)
- `docs/DATA_INGESTION.md` — corpus, chunking, MCP
- `docs/BUILD_PLAN.md` — phase order and exit criteria
- `docs/TEST_PLAN.md` — acceptance tests
- `docs/SDK_NOTES.md` — verified LiveKit API surface
- `docs/DEV_JOURNAL.md` — append an entry after every verified, committed step (see
  Working style below); read it to catch up on prior reasoning fast

---

## Working style

- **Plan before implementing** anything non-trivial. Show the plan, wait for approval.
- **One phase at a time.** Do not jump ahead in `BUILD_PLAN.md`.
- **Run things.** Don't say "this should work" — execute and show output.
- **Diagnose before fixing.** When something breaks, explain the root cause first.
- **Cite requirement IDs** in commits and comments where relevant.
- **Log-then-commit, strictly, after every completed step.** The sequence is fixed and
  does not skip steps, even under time pressure:
  1. Do the work.
  2. Verify it (run it, check output, confirm no secrets before any `git add`).
  3. Commit the work on its own.
  4. Write a `docs/DEV_JOURNAL.md` entry for it — detailed, and written so the
     underlying concepts are understandable later, not just the diff. This journal is
     the owner's interview-prep record of the project, not a changelog.
  5. Commit the journal entry **separately** from the work it describes.
  Never bundle a journal update into the same commit as the work — the history should
  show "the change" and "the reflection on the change" as distinct commits.

---

## Current status

*Update this as you go — it's how a new session gets oriented fast.*

- [x] Phase 0 — Accounts and scaffolding
- [x] Phase 1 — Audio round-trip
- [x] Phase 2 — Corpus and ingestion
- [ ] Phase 3 — Grounding and citations
- [ ] Phase 4 — UX
- [ ] Phase 5 — Deployment
- [ ] Phase 6 — Testing and submission

**Now working on:** Ready to start Phase 3 (grounding and citations) — the graded
feature. Corpus is live in Supabase: 51 chunks (resume, `context.md`, 6 curated GitHub
repos) via `ingestion/ingest.py`, re-runnable and idempotent (`uv run python -m
ingestion.ingest`). All Phase 2 `BUILD_PLAN.md` exit criteria pass, verified with
`uv run python -m ingestion.validate`: chunk count in range, no floor/ceiling
violations, no duplicate hashes, all 5 spot-checks return the correct top chunk, the
out-of-scope refusal check passes. Retrieval is **hybrid** (dense cosine similarity for
eligibility/threshold-gating + Postgres full-text keyword ranking for ordering among
eligible candidates via Reciprocal Rank Fusion) — added mid-phase after a real spot-
check failure, see `docs/DEV_JOURNAL.md`'s 2026-08-18 validation entry. `match_chunks`
now takes `query_embedding` **and** `query_text`; Phase 3's `retrieval.py` should call
it with both from the start.
**Blocked by:** Nothing functionally. Four things worth attention when they become
relevant: (1)/(2) the Phase 1 latency (LLM TTFT ~2.5s avg, one 7s spike) and barge-in
timing (~455ms) numbers are still open, unchanged since Phase 1 — revisit once Phase
3's real system prompt exists; (3) `RETRIEVAL_THRESHOLD=0.5` is empirically grounded
against real out-of-scope scores for this corpus, but is explicitly interim — final
tuning happens in Phase 3 against the full 20-question `TEST_PLAN.md` suite; (4)
`bge-small-en-v1.5` has a real, demonstrated weakness anchoring on short acronyms/
numbers inside longer passages (the CGPA spot-check) — hybrid search compensates for
this specific case, but a differently-phrased factual query could still expose the same
underlying weakness; worth keeping in mind when writing Phase 3's test questions.
**Decisions made this session:** GitHub content ingests via plain REST + PAT, not an
MCP client — walked through the real trade-offs with the owner before choosing; see
`ARCHITECTURE.md` ADR-002/ADR-003 amendments. GitHub ingestion is curated to 6 repos
matching what the resume/`context.md` narrative actually references, not all 22
non-fork repos (would have been 212 chunks of mostly-irrelevant coursework). `corpus/*`
is gitignored except `README.md` — resume/`context.md` carry personal contact info,
so source documents are ingested but never pushed to public git history.
**Decisions made in earlier sessions:** `GEMINI_MODEL` defaults to the
`gemini-flash-latest` rolling alias, not a pinned version — `gemini-2.5-flash` (the
plugin's own compiled-in default) is confirmed dead (404 "no longer available to new
users") despite still appearing in the `/models` listing. `agent/main.py` deliberately
omits `agent_name` on `@server.rtc_session()` to keep automatic dispatch (FR-1.4) — a
non-empty `agent_name` silently switches to explicit-dispatch-only.
