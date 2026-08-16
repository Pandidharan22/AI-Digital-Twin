# Build Plan — 7 Days

**The one rule that matters:** do not start a phase until the previous phase's exit
criteria pass. Building the pipeline and the RAG layer simultaneously is the single
most common way this project dies — when it breaks you cannot tell which half is wrong.

Each phase has: setup, what to build, exit criteria, and common failure modes.

---

## Phase 0 — Accounts and keys (2 hours, do before Day 1)

Get every credential first. Nothing kills momentum like stopping mid-build to verify an
email.

- [ ] **LiveKit Cloud** — sign up, create project, copy `LIVEKIT_URL`, `LIVEKIT_API_KEY`,
      `LIVEKIT_API_SECRET`
- [ ] **Deepgram** — sign up (no card), claim $200 credit, copy `DEEPGRAM_API_KEY`.
      *This one key covers both STT and TTS.*
- [ ] **Google AI Studio** — create `GEMINI_API_KEY`, confirm free tier active
- [ ] **Supabase** — new project, enable `vector` extension, copy connection string
- [ ] **GitHub** — fine-grained PAT, read-only public repos
- [ ] Python 3.11+, Node 18+, `uv` installed
- [ ] Repo created, `.gitignore` includes `.env` **before first commit**

**Exit:** every key in `.env`, `.env` gitignored, `.env.example` committed.

---

## Phase 1 — Audio round-trip (Day 1)

**Goal: hear a bot talk back. No intelligence, no retrieval.**

This is deliberately dumb. You are proving WebRTC, worker dispatch, STT, LLM, and TTS
all connect before adding anything that could obscure a transport bug.

### Build

1. Clone LiveKit's `agent-starter-python` as your skeleton — it ships with the pipeline,
   turn detection, noise cancellation, and metrics already wired.
2. **Verify the SDK surface before writing code.** The 1.0 release replaced
   `VoicePipelineAgent` with `AgentSession`. Have Claude Code read the installed
   package's docs/source rather than reproducing a tutorial from memory.
3. Swap plugins to your stack: Deepgram STT, Gemini LLM, Deepgram Aura TTS, Silero VAD.
4. Run the worker locally in dev mode.
5. Connect via LiveKit's hosted playground or the starter frontend.

### Exit criteria

- [ ] Worker connects and logs "registered"
- [ ] Browser joins, mic permission granted
- [ ] You speak → accurate transcript in worker logs
- [ ] Bot replies in audible speech
- [ ] Interrupting mid-reply stops playback
- [ ] Round-trip feels under ~2s

### Common failures

| Symptom | Cause |
|---|---|
| Worker registers, never joins | Dispatch config; check room naming/agent name |
| No audio out | TTS key wrong, or plugin not installed |
| Transcript empty | Mic not published, or wrong track subscription |
| `VoicePipelineAgent` not found | Outdated tutorial — use `AgentSession` |

**Do not proceed until every box is ticked.** Everything downstream assumes this works.

---

## Phase 2 — Corpus and ingestion (Day 2)

**Goal: a populated, validated vector store. Zero voice work today.**

### Build

1. Write `corpus/context.md` by hand first (see `DATA_INGESTION.md` §2). Highest-value
   hour in the project.
2. Gather resume, project descriptions, LinkedIn export.
3. Supabase: create `chunks` table, enable pgvector, add the similarity search function.
4. Loaders: PDF, markdown, GitHub MCP.
5. Semantic chunker with contextual prefixing.
6. Local embedder.
7. Idempotent upsert.
8. **Validation script** — the 5 spot-check queries.

### Exit criteria

- [ ] 40–150 chunks in Supabase
- [ ] Every chunk has meaningful `source` and `section`
- [ ] Re-running produces zero duplicates
- [ ] All 5 spot-check queries return the correct top chunk
- [ ] Out-of-scope query ("favourite pizza") scores below threshold

Last item is critical — that's your refusal mechanism proving itself at the data layer,
where it's easy to debug.

---

## Phase 3 — Grounding and citations (Days 3–4)

**Goal: the graded feature. Budget two full days.**

### Build

**Day 3 — retrieval into the agent**
1. `retrieval.py` — query embedding, pgvector search, threshold gate, `no_match` signal
2. Register `search_my_background` as a function tool
3. Write the system prompt into `agent/prompts/system_prompt.md`
4. Test by voice: does it retrieve, ground, and refuse?

**Day 4 — citation emission**
5. `citations.py` — publish payload to data channel, **before** LLM generation
6. Frontend listener for the `citations` topic
7. Source cards bound to `turn_id`
8. `no_match` state clears stale cards
9. Tune the threshold against the full test set

### Exit criteria

- [ ] Factual question → correct answer + correct source card
- [ ] Cards appear **before** the bot starts speaking
- [ ] Out-of-scope question → graceful refusal + "no source" chip
- [ ] "You worked at Google, right?" → correction, not agreement
- [ ] Bot never speaks source names aloud
- [ ] No markdown artifacts audible in speech
- [ ] Zero fabrications across the 20-question test set

### Common failures

| Symptom | Fix |
|---|---|
| Bot answers without calling the tool | Strengthen prompt rule 1; check tool description clarity |
| Bot agrees with false premises | Add explicit rule 5; verify it searches before agreeing |
| Cards appear after speech | Publishing after LLM call — move it before |
| Refuses valid questions | Threshold too high; lower and retest both suites |
| Reads "asterisk asterisk" aloud | Prompt isn't enforcing plain text |

---

## Phase 4 — UX (Day 5)

**Goal: it looks finished.**

Priority order — do them in this sequence, stop when the day ends:

1. **Connection states** (`connecting`/`listening`/`thinking`/`speaking`/`error`).
   Highest value. Silence with no indicator reads as broken.
2. **Mic permission flow** — explain before requesting.
3. **Transcript panel** — both sides, auto-scroll.
4. **Sources sidebar** — proper cards, not raw JSON.
5. **Suggested questions** — the four from `CITATION_SPEC.md` §7. You're choosing what
   the evaluator tests first.
6. **Mobile responsive** — sources become a collapsible sheet.
7. **Error states** — actionable messages.

### Exit criteria

- [ ] Never a silent unexplained state
- [ ] Works on mobile Safari
- [ ] A stranger could use it with no instructions
- [ ] Suggested questions visible on load

---

## Phase 5 — Deployment (Day 6)

**Goal: a link that works when someone else clicks it, cold.**

### Build

1. Deploy token service (Fly.io / Render)
2. Deploy agent worker as a **long-running process**, not a web service
3. Deploy frontend (Vercel)
4. Wire production env vars everywhere
5. **Test cold** — new browser profile, phone on cellular, not your dev machine
6. Set up keep-warm ping
7. Set up GitHub Actions ingestion cron

### Exit criteria

- [ ] Link works from a device that never saw the project
- [ ] Works on mobile cellular
- [ ] Cold start under 15s
- [ ] Worker survives 30 minutes idle then responds
- [ ] Zero secrets in the frontend bundle (inspect it)
- [ ] Scheduled ingestion runs successfully once

**The cold-start test is not optional.** A sleeping free-tier worker is the single most
common reason a working project reads as broken during evaluation.

---

## Phase 6 — Hardening and submission (Day 7)

### Morning — testing
1. Full `TEST_PLAN.md` suite
2. Measure and record latency across 20 turns
3. Fix any P0 bugs found
4. Have someone else use it while you watch silently. Note every hesitation.

### Afternoon — submission artefacts
5. **`ARCHITECTURE.md` writeup** — fill in all ADR "Outcome" fields with real numbers
6. **Public `README.md`** — what it is, live link, quickstart, stack, design highlights
7. Repo hygiene — no secrets, clean history, working setup instructions
8. Optional: 60-second screen recording as insurance against demo-day failure
9. Send: link + repo + writeup

### Exit criteria

- [ ] All acceptance tests in `SRS.md` §6 pass
- [ ] Latency numbers recorded
- [ ] ADR outcomes filled with real findings
- [ ] Clean clone → follow README → runs

---

## If you fall behind

Cut in this order:

1. Live-facts MCP tool (P2)
2. Latency display (P2)
3. Automated ingestion cron — run manually, document the design (P1)
4. Session memory (P1)
5. Mobile polish — desktop-only, say so (P1)

**Never cut:** citations, refusal behaviour, hosted link, basic UX states. Those are the
brief.

---

## Daily discipline

- **Start** by re-reading the phase's exit criteria.
- **End** by ticking boxes honestly. A half-passing criterion is a failing one.
- **Commit** at every green checkpoint so you always have a working state to fall back to.
- **Log decisions** in `ARCHITECTURE.md` as you make them. Reconstructing your reasoning
  on Day 7 produces a vague writeup; capturing it live produces a sharp one.
