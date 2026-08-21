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
| LLM | Gemini Flash-Lite | Free tier; ≥15 RPM (`gemini-3.5-flash-lite`, pinned, verified live 2026-08-21) — handle 429s |
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
- [x] Phase 3 — Grounding and citations (core build + Suite C voice run done;
      20-turn latency measurement still open)
- [ ] Phase 4 — UX (connection states, mic flow, suggested questions, and the
      transcript panel are done; mobile polish still open)
- [ ] Phase 5 — Deployment (first live deployment done and verified; several
      hardening items still open — see below)
- [ ] Phase 6 — Testing and submission

**Now working on:** Phase 3's build and voice-verification are done —
`TEST_PLAN.md` Suite C ran by voice, 7/7 pass (2026-08-21). `agent/retrieval.py`
(embed + hybrid pgvector search + threshold gate, tuned to **0.55**),
`agent/twin_agent.py` (`TwinAgent` with `search_my_background`),
`agent/citations.py` (publishes before generation, per ADR-005), the real
`agent/prompts/system_prompt.md`, and `agent/main.py` are all live and verified.
Only NFR-1.1/1.2's formal 20-turn latency measurement is still unmeasured.

Phase 4 has three of five prioritized items done: `AgentStatus.tsx` (FR-5.2,
via `useVoiceAssistant()`), `MicPermissionNotice.tsx` (explainer + a
`mediaDevicesError`-driven denied-state message), and `SuggestedQuestions.tsx`
(FR-5.4, `CITATION_SPEC.md` §7's four demo questions — with question 1 swapped
to `TEST_PLAN.md`'s A2 phrasing since A1's literal wording is the known
retrieval-ranking gap noted below). `TranscriptPanel.tsx` (FR-5.1) is also
done, using `@livekit/components-react`'s own `useTranscriptions()` hook —
the same mechanism behind LiveKit's Agent Console transcript view, no
agent-side changes needed. Still open: mobile responsive layout.

**Phase 5, first live deployment is up and verified end-to-end**
(2026-08-21): Token Service on Render
(`https://voice-twin-api-46lk.onrender.com`, via the `render.yaml` Blueprint
and a Token-Service-only `api/requirements.txt` kept separate from the shared
`pyproject.toml`), frontend on Vercel
(`https://ai-digital-twin-blue.vercel.app`), agent worker running as a
long-lived local process (LiveKit dispatch is outbound-only, so this works —
see `docs/DEPLOYMENT.md` Sec2's own sanctioned fallback). Verified cold, via
unauthenticated `curl` and a browser tab with no prior site history, not
trusted from a dashboard: the whole chain connects and the agent speaks its
greeting. One real bug caught and fixed along the way — Vercel's Deployment
Protection was silently gating the "public" link behind a Vercel login;
disabled and re-verified. See `docs/DEV_JOURNAL.md`'s 2026-08-21 deployment
entries for the full account.

Still open before Phase 5's exit criteria are fully met: move the worker off
the local machine to Fly.io, the 30-minute-idle-then-cold-open test, mobile
Safari/cellular verification, the GitHub Actions ingestion cron, and
confirming zero secrets in the frontend bundle by inspection.

**Blocked by:** Nothing functionally. Open items: (1)/(2) the Phase 1 latency (LLM
TTFT ~2.5s avg, one 7s spike) and barge-in timing (~455ms) numbers are still
unrevisited since Phase 1; (3) `CITATION_SPEC.md` §7's literal first demo
question ("What's your most recent role?") still fails to retrieve the
Freelance experience chunk in the top-4 at every threshold tested
(0.50–0.65) — worked around in the UI by using `TEST_PLAN.md`'s A2 phrasing
instead (2026-08-21), but the underlying retrieval-ranking gap itself is
still unfixed and still needs its own investigation before final submission;
(4) `bge-small-en-v1.5` has a real, demonstrated weakness anchoring on short
acronyms/numbers inside longer passages (the CGPA spot-check) — hybrid search
compensates for that specific case, but the threshold sweep also surfaced a
*different* weakness class: coincidental vocabulary-proximity false positives
(e.g. "salary" vs. an unrelated Loan-Eligibility-API README) that threshold
tuning alone can't fully separate from real matches.
**Decisions made this session:** GitHub content ingests via plain REST + PAT, not an
MCP client — walked through the real trade-offs with the owner before choosing; see
`ARCHITECTURE.md` ADR-002/ADR-003 amendments. GitHub ingestion is curated to 6 repos
matching what the resume/`context.md` narrative actually references, not all 22
non-fork repos (would have been 212 chunks of mostly-irrelevant coursework). `corpus/*`
is gitignored except `README.md` — resume/`context.md` carry personal contact info,
so source documents are ingested but never pushed to public git history.
**Decisions made in earlier sessions:** `GEMINI_MODEL` defaults to the pinned
`gemini-3.5-flash-lite` (switched from the `gemini-flash-latest` rolling alias in
Phase 3 after a live 429 — see `docs/DEV_JOURNAL.md`'s 2026-08-21 entry: the full-
Flash tier `gemini-flash-latest` resolves to is only 5 RPM on the free tier, vs
`gemini-3.5-flash-lite`'s verified ≥15 RPM, with correct tool-calling behaviour
confirmed live against the real system prompt and tool across three cases —
greeting, factual question, adversarial false-premise). Deliberately pinned rather
than another rolling alias — the alias was supposed to dodge model retirement, but
it's exactly what silently cut the RPM budget in the first place when Google moved
its target underfoot with no warning; a pinned ID can only fail loudly (404), not
quietly. `gemini-2.5-flash` and `gemini-2.5-flash-lite` (this project's earlier
choices) are both confirmed dead (404 "no longer available to new users") despite
still appearing in the `/models` listing. `agent/main.py` deliberately omits
`agent_name` on `@server.rtc_session()` to keep automatic dispatch (FR-1.4) — a
non-empty `agent_name` silently switches to explicit-dispatch-only.
