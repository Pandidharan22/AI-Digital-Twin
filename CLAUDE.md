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
| LLM | Gemini Flash | Free tier; ~10 RPM — handle 429s |
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

---

## Working style

- **Plan before implementing** anything non-trivial. Show the plan, wait for approval.
- **One phase at a time.** Do not jump ahead in `BUILD_PLAN.md`.
- **Run things.** Don't say "this should work" — execute and show output.
- **Diagnose before fixing.** When something breaks, explain the root cause first.
- **Cite requirement IDs** in commits and comments where relevant.

---

## Current status

*Update this as you go — it's how a new session gets oriented fast.*

- [ ] Phase 0 — Accounts and scaffolding
- [ ] Phase 1 — Audio round-trip
- [ ] Phase 2 — Corpus and ingestion
- [ ] Phase 3 — Grounding and citations
- [ ] Phase 4 — UX
- [ ] Phase 5 — Deployment
- [ ] Phase 6 — Testing and submission

**Now working on:** [phase]
**Blocked by:** [anything]
**Decisions made this session:** [log them so ADRs can be filled in later]
