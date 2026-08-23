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
      transcript panel are done; mobile audited and its one real gap fixed —
      real-device Safari/cellular verification still open)
- [ ] Phase 5 — Deployment (fully hosted on Render/Vercel/Fly.io, verified
      end-to-end; a few hardening items still open — see below)
- [ ] Phase 6 — Testing and submission

**Now working on:** Phase 3's build and voice-verification are done —
`TEST_PLAN.md` Suite C ran by voice, 7/7 pass (2026-08-21). `agent/retrieval.py`
(embed + hybrid pgvector search + threshold gate, tuned to **0.55**),
`agent/twin_agent.py` (`TwinAgent` with `search_my_background`),
`agent/citations.py` (publishes before generation, per ADR-005), the real
`agent/prompts/system_prompt.md`, and `agent/main.py` are all live and verified.
NFR-1.1/1.2's 20-turn latency measurement is now partially done (2026-08-22):
`tests/measure_latency.py` + `tests/parse_latency_log.py` ran a real 20-turn
suite against the live production worker (text input over `lk.chat`, same
substitution `TEST_PLAN.md` Suite C used) and found `llm_ttft` median 1066ms/
p95 1276ms — roughly 2x the NFR-1.4 target, a real and stable finding, not an
outlier. `e2e_latency` and the STT-stage numbers came back `None` on every
turn — a genuine method limit (those fields are anchored to the STT/VAD
end-of-utterance event, which text injection never fires), not a bug; a real
voice pass is still needed to fill in `TEST_PLAN.md`'s Total/STT rows. See
`docs/TEST_PLAN.md` Sec3 and `docs/DEV_JOURNAL.md`'s 2026-08-22 entry.

Phase 4 has three of five prioritized items done: `AgentStatus.tsx` (FR-5.2,
via `useVoiceAssistant()`), `MicPermissionNotice.tsx` (explainer + a
`mediaDevicesError`-driven denied-state message), and `SuggestedQuestions.tsx`
(FR-5.4, `CITATION_SPEC.md` §7's four demo questions, now the literal spec
wording again — see the A1 fix below). `TranscriptPanel.tsx` (FR-5.1) is also
done, using `@livekit/components-react`'s own `useTranscriptions()` hook —
the same mechanism behind LiveKit's Agent Console transcript view, no
agent-side changes needed. UI was redesigned once already after owner
feedback on the first live deployment (2026-08-21): single-column blended
layout (no boxed transcript, no half-screen citations panel), a custom
`MicToggle.tsx` replacing `ControlBar`, and `CitationsPanel.tsx` now labels
each source by document type (Resume / Notes (context.md) / `<repo>` —
README.md) instead of showing the raw retrieved excerpt.

**Mobile layout audited and its one real gap fixed (2026-08-22).** Measured
actual rendered geometry (`getBoundingClientRect`/`getComputedStyle`, not
visual screenshots — this environment's Browser pane wasn't visibly
displayed, so screenshot compositing wasn't available) against the real
running app at 375px: the existing flex/`rem`-based single-column layout was
already fully fluid with zero horizontal overflow anywhere. The one real gap
— `.mic-toggle`, the app's only interactive control, at 33px tall vs. the
44px comfortable touch-target guideline — is now fixed via one scoped
`@media (max-width: 480px)` block in `App.css`, desktop unchanged. Real iOS/
Android Safari behavior (mic permission prompts, audio autoplay policy) is
still unverified — needs an actual device, per `TEST_PLAN.md` U5/U6. See
`docs/DEV_JOURNAL.md`'s 2026-08-22 entry.

**Phase 5 is fully hosted and verified end-to-end** (2026-08-21/22): Token
Service on Render (`https://voice-twin-api-46lk.onrender.com`, via the
`render.yaml` Blueprint and a Token-Service-only `api/requirements.txt` kept
separate from the shared `pyproject.toml`), frontend on Vercel
(`https://ai-digital-twin-blue.vercel.app`), and the agent worker now on
**Fly.io** (`agent/Dockerfile` + `fly.toml`, app `voice-twin-worker`,
`performance-2x`/4GB (dedicated CPU) in `sin` — moved off the local machine
that hosted it through the first deployment. Briefly downgraded to
`shared-cpu-2x`/2GB (~$11-15/month vs. `performance-2x`'s ~$60-70/month)
after a clean test, then reverted the same day when it regressed live in
production with the exact same timeout failure it had before — a shared
VM's performance depends on other tenants on the same host, so one passing
test wasn't proof of reliability. Settled on `performance-2x` for good; see
the 2026-08-22 journal entries for both the downgrade attempt and the
revert. No free tier on Fly.io; a card on file is billed per-second. True
idle-autostop isn't
available for this worker (no `[http_service]` for Fly's proxy to gate on,
since the worker is outbound-only) — `flyctl scale count 0`/`1` is the
manual stop/start toggle instead. The Fly move itself surfaced four
real bugs, each fixed and verified via a live redeploy, not assumed: (1)
`uv sync` resolving PyPI's CUDA torch build on Linux, fixed by pinning
torch to `download.pytorch.org/whl/cpu` as a *direct* dependency (source
overrides didn't bind to it as a transitive-only one); (2) Fly's `bom`
region being deprecated for new resources, switched to `sin`; (3)
`shared-cpu-2x` throttling badly enough under concurrent cold-starts to
blow even a 30s `initialize_process_timeout`, fixed by moving to dedicated
CPU; (4) the actual dominant cold-start cost turning out to be
`SentenceTransformer`'s constructor hitting Hugging Face Hub over the
network on every start (~19s, unauthenticated), fixed by baking the model
into the image at build time and setting `HF_HUB_OFFLINE=1`. Full account
in `docs/DEV_JOURNAL.md`'s 2026-08-21/22 entry. Earlier in Phase 5: Vercel's
Deployment Protection was found silently gating the "public" link behind a
Vercel login; disabled and re-verified.

**Render token API cold-start is now mitigated**: `.github/workflows/keep-warm.yml`
pings `/health` every 10 minutes (GitHub Actions `schedule` + `workflow_dispatch`),
per `docs/DEPLOYMENT.md` Sec4's own prescription — implemented and verified live
(2026-08-22) after the owner hit an uncovered case: Render's free tier had
spun down, cold start took ~60-90s (worse than the doc's 10-30s estimate),
compounding with that session's `shared-cpu-2x` regression above. A separate,
real finding from that same incident: DNS lookups for `onrender.com` were
returning wrong answers on the owner's local network even against an explicit
`8.8.8.8` query — confirmed local-network-specific (likely router/ISP-level
filtering), not a Render problem, and left for the owner to resolve since it's
outside this session's reach.

`POST /token` is now rate-limited (2026-08-23): 5/minute + 30/hour per client
IP via `slowapi`, with `render.yaml`'s `startCommand` fixed to pass
`--forwarded-allow-ips='*'` so the limiter sees each real visitor's IP rather
than Render's load balancer's (verified against uvicorn's real installed
source — its `ProxyHeadersMiddleware` only trusts `127.0.0.1` by default).
Verified locally end-to-end (5 requests succeed, 6th/7th `429` with CORS
intact, `/health` unaffected); not yet pushed, and the
`--forwarded-allow-ips` fix's correctness against Render's actual proxy is
verified by reasoning + source, not yet empirically confirmed with two real
distinct client IPs post-deploy. See `docs/TEST_PLAN.md` Sec6 and
`docs/DEV_JOURNAL.md`'s 2026-08-23 entry.

`POST /token`'s rate limiting is now pushed and confirmed live
(2026-08-23): a real 6-request burst against production Render showed
`200 200 200 200 200 429`, `/health` unaffected. Distinguishing true
per-visitor limiting from "the whole site sharing one bucket" still needs a
second real distinct client IP to test from, which this session doesn't
have — flagged, not closed.

Zero-secrets-in-frontend-bundle is also now reverified (2026-08-23), not just
spot-checked once at first deploy: `web/vite.config.ts` has no `envDir`
override (Vite structurally can't read the repo-root `.env`), and both a
local production build and the **live deployed bundle** were scanned for
every real secret's literal value plus generic secret-shape patterns —
clean both times. See `docs/TEST_PLAN.md` Sec6.

An automated test suite now exists (2026-08-23): `tests/test_citations.py`
(unit, `CITATION_SPEC.md` Sec4's payload contract, no live infra) and
`tests/test_retrieval_suite.py` (integration, Suite A/B against the real
corpus via the real `agent/retrieval.py`). Run via `uv run pytest`
(`-m "not integration"` for the fast path). Building it surfaced and fixed
one more real Suite A gap (A5, "What did you study?" — same missing-framing
root cause as A1) and found one new, deliberately-not-fixed trade-off (A7,
"hardest technical problem" — the right chunk scores 0.51, just under the
0.55 gate; fixing it would cost more Suite B false accepts than it's worth).
Current corpus state: 11/13 Suite A, 6/7 Suite B, with all three known gaps
(A7, CGPA, salary) tracked as `xfail(strict=True)`, not silently accepted.
See `docs/TEST_PLAN.md` Sec1-2 and `docs/DEV_JOURNAL.md`'s 2026-08-23 entry.

Still open before Phase 5's exit criteria are fully met: the
30-minute-idle-then-cold-open test (now easier to re-verify with the keep-warm
cron in place — worth confirming it actually prevents the sleep, not just
assuming), mobile Safari/cellular verification, and the GitHub Actions
**ingestion** cron (distinct from the keep-warm cron above — refreshes the
corpus from GitHub, not yet built).

**Blocked by:** Nothing functionally. Open items: (1) the Phase 1 barge-in
timing (~455ms) number is still unrevisited since Phase 1 — see (2a) below for
the LLM-latency half, which is no longer stale; (2a) NFR-1's LLM-latency
numbers are now real and current (2026-08-22, superseding the stale Phase 1
figures): `llm_ttft` median 1066ms/p95 1276ms across a real 20-turn production
run — see `docs/TEST_PLAN.md` Sec3. Total end-to-end and STT-stage numbers are
still unmeasured (need a real voice pass, not text input); (3) **fixed
(2026-08-22)** — `CITATION_SPEC.md` §7's literal first demo question ("Tell me
about your most recent role") previously failed to retrieve the Freelance
experience chunk in the top-4 at every threshold tested (0.50–0.65); root
cause was the chunk's own text never stating it was the most recent role, now
fixed in `ingestion/loaders/pdf_loader.py` and reverified at rank 0 — see
`docs/DEV_JOURNAL.md`'s 2026-08-22 entry. The frontend's suggested-question
workaround (`TEST_PLAN.md`'s A2 phrasing) has been reverted back to the
original spec wording and, along with the mobile mic-button fix, **pushed and
live** (2026-08-22/23, verified via a direct curl of the deployed bundle);
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
