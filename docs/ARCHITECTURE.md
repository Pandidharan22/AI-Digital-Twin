# Architecture — Voice Twin

This is both a build spec and the seed of your submission writeup. The ADR section is
the part evaluators actually read closely — fill in the "Outcome" notes as you build.

---

## 1. System overview

```
┌─────────────┐         WebRTC          ┌──────────────────┐
│   Browser   │◄───────audio/data──────►│  LiveKit Cloud   │
│   (React)   │                         │      (SFU)       │
└──────┬──────┘                         └────────┬─────────┘
       │                                          │
       │ POST /token                              │ agent joins room
       ▼                                          ▼
┌─────────────┐                         ┌──────────────────┐
│   FastAPI   │                         │   Agent Worker   │
│   Token     │                         │    (Python)      │
│   Service   │                         └────────┬─────────┘
└─────────────┘                                  │
                                    ┌────────────┼────────────┐
                                    ▼            ▼            ▼
                              ┌─────────┐  ┌─────────┐  ┌──────────┐
                              │Deepgram │  │ Gemini  │  │ Deepgram │
                              │ Nova-3  │  │  Flash  │  │  Aura-2  │
                              │  (STT)  │  │  (LLM)  │  │  (TTS)   │
                              └─────────┘  └────┬────┘  └──────────┘
                                                │ tool call
                                                ▼
                                         ┌──────────────┐
                                         │  Supabase    │
                                         │  pgvector    │
                                         └──────▲───────┘
                                                │ writes
                                         ┌──────┴───────┐
                                         │  Ingestion   │
                                         │  Job (cron)  │
                                         └──────▲───────┘
                                                │ reads
                                    ┌───────────┴───────────┐
                                    │  GitHub MCP  │  Local │
                                    │  (official)  │  files │
                                    └──────────────────────-┘
```

---

## 2. Components

### 2.1 Agent Worker (Python)
The brain. A long-running process, **not** a request-response service. It connects
*outbound* to LiveKit Cloud and waits for job dispatch — which means it needs no public
IP, no inbound ports, and no tunnelling. It runs fine from a laptop for a live demo.

Responsibilities: orchestrate the voice pipeline, own the system prompt, expose the
retrieval tool, publish citation payloads, handle errors.

### 2.2 Token Service (FastAPI)
Small and stateless. Mints short-lived LiveKit access tokens so the browser never holds
API secrets. Exposes `POST /token` and `GET /health` (the latter doubles as the
keep-warm target).

### 2.3 Frontend (React)
Room connection, mic controls, audio rendering — mostly assembled from LiveKit's
prebuilt components. The custom work is thin: a transcript panel and a **sources
sidebar** that listens on the data channel.

### 2.4 Vector Store (Supabase Postgres + pgvector)
One table. Chunks with embeddings and metadata. Queried by cosine similarity at runtime;
written only by the ingestion job.

### 2.5 Ingestion Job
Offline batch. Reads local documents and GitHub data (via official MCP), chunks,
embeds locally, upserts. Runs on a schedule. **Never on the request path.**

---

## 3. Request flow — one conversational turn

1. Visitor speaks. Browser publishes audio track to the room.
2. Worker receives audio, streams it to Deepgram STT. Partial transcripts return live.
3. Turn detector determines the utterance ended.
4. Final transcript goes to Gemini Flash with the system prompt and session history.
5. Gemini decides whether a factual claim is needed. If yes → calls
   `search_my_background(query)`.
6. Tool embeds the query, runs pgvector similarity search, applies the threshold.
7. **Before returning to the LLM**, the worker publishes the retrieved sources to the
   data channel. Frontend renders source cards immediately.
8. Chunks return to Gemini as tool output. Gemini composes a grounded, speakable reply.
9. Reply tokens stream into Deepgram Aura-2; audio streams back into the room as
   generated.
10. Browser plays audio. Transcript updates. Source cards are already on screen.

The critical design point is **step 7 before step 8**. Publishing citations before
generation means the UI shows grounding *as* the answer arrives, not after. It also
means the citation reflects what was actually retrieved, not what the LLM claims it
used — the LLM cannot fake a source it wasn't given.

---

## 4. Architecture Decision Records

### ADR-001 — Chained STT→LLM→TTS pipeline over speech-to-speech

**Context.** LiveKit supports two agent shapes: a chained pipeline of three models, or
a single realtime speech-to-speech model. Speech-to-speech has lower latency and more
natural prosody.

**Decision.** Chained pipeline.

**Rationale.** The brief's hard requirement is source-cited answers. A chained pipeline
has a **text checkpoint** between hearing and speaking, and that checkpoint is exactly
where retrieval, grounding enforcement, and citation emission must happen. Speech-to-
speech collapses that checkpoint and makes reliable grounding substantially harder.
Chaining also makes each provider independently swappable — if TTS quality disappoints,
I replace one component, not the whole system.

**Trade-off accepted.** Higher latency than S2S. Mitigated by streaming every stage and
selecting a fast-first-token model.

**Outcome.** *[Fill in after building: measured latency, whether grounding held.]*

---

### ADR-002 — Curated vector store for serving, MCP for freshness

**Context.** Two ways to give the agent knowledge: precompute embeddings into a vector
store, or fetch live from source APIs (GitHub, LinkedIn) at query time via MCP. Live
fetch is appealing because the corpus never goes stale.

**Decision.** Both, at different layers. Vector store serves queries. MCP feeds the
offline ingestion pipeline.

**Rationale.** MCP and RAG are not alternatives — MCP is a *protocol for reaching data
sources*, RAG is a *pattern for grounding generation*. An agent that calls an MCP tool
and grounds its answer in the result is doing RAG. The real question is *when* you
fetch, and for a voice application the answer is decisively "not during the call":

- **Latency.** The budget to first audio is ~1.5s. A live API round-trip plus parsing
  consumes most of it before the LLM starts. Precomputed vector search returns in
  ~20–50ms.
- **Freshness cadence mismatch.** A resume doesn't change mid-conversation. The
  freshness window that matters is *days*. Paying a per-query fetch tax to capture
  weekly updates is a bad trade.
- **Citation quality.** A raw README is a wall of badges and setup instructions.
  Chunking and metadata assignment during ingestion is what makes a *clean, citable
  unit* possible. Live blobs cite as "GitHub API response" — technically a source, not
  a useful one.
- **Availability coupling.** A live dependency that rate-limits or goes down during
  evaluation fails the demo. A precomputed store has no query-time external dependency.

Freshness is solved where it belongs — **offline** — by scheduling ingestion, not by
moving retrieval onto the hot path.

**Trade-off accepted.** Corpus is stale between ingestion runs. Acceptable because the
staleness window is hours, and the refresh is automated.

**Outcome.** *[Fill in: ingestion cadence chosen, refresh runtime.]*

---

### ADR-003 — GitHub via official MCP; LinkedIn via official data export only

**Context.** GitHub publishes an official, actively maintained MCP server. LinkedIn
publishes none. Every available LinkedIn MCP server is third-party, and the most popular
ones drive a logged-in browser session using a scraped cookie.

**Decision.** GitHub through the official MCP server. LinkedIn content enters only via
the Owner's own official LinkedIn data export, ingested as local files.

**Rationale.** Cookie-driven LinkedIn automation violates LinkedIn's User Agreement and
risks account restriction. The value it adds — profile text I already possess and can
export officially — does not justify a ToS violation on a portfolio project intended to
demonstrate judgement. The official export gives the same content, legally, and it is
static enough that manual refresh is not a burden.

**Trade-off accepted.** LinkedIn content requires periodic manual re-export.

**Outcome.** *[Fill in.]*

---

### ADR-004 — Threshold-gated retrieval as the anti-hallucination mechanism

**Context.** Prompt instructions alone ("only answer from context") are probabilistic.
Under pressure — leading questions, false premises — models drift toward agreeableness.

**Decision.** Enforce grounding **structurally**: the retrieval tool applies a
similarity threshold and returns an explicit `no_match` signal when nothing qualifies.
The prompt then has an unambiguous, non-negotiable branch to follow.

**Rationale.** A prompt rule the model *might* follow is weaker than an empty result set
the model *cannot* answer from. Moving the decision out of the prompt and into code
makes refusal deterministic where it matters most.

**Trade-off accepted.** A poorly tuned threshold causes false refusals on legitimate
questions. Mitigated by tuning against the test set in `TEST_PLAN.md`.

**Outcome.** *[Fill in: final threshold value and how you tuned it.]*

---

### ADR-005 — Citations published before generation, rendered not spoken

**Context.** Citations could be spoken aloud, appended to the transcript, or surfaced
as UI elements. They could be emitted by the LLM or by the retrieval code.

**Decision.** The **worker** publishes the actual retrieved chunks to the data channel
before the LLM generates. The UI renders them as cards. Audio never speaks them.

**Rationale.** Two reasons. First, **audio ergonomics**: "according to resume dot pdf,
section experience" destroys conversational flow. Second, and more important,
**integrity**: if the LLM emitted citations, it could name a source it never received.
Emitting from the retrieval layer means the citation is a record of what actually
happened, not a claim about it.

**Trade-off accepted.** Audio-only consumers see no citations. Acceptable — the brief
asks for a link with a UX, not a phone line.

**Outcome.** *[Fill in.]*

---

### ADR-006 — Local embedding model over hosted embedding API

**Context.** Embeddings needed for both ingestion and query. Options: hosted API
(Gemini, OpenAI) or local `sentence-transformers`.

**Decision.** Local model (`bge-small-en-v1.5` or `all-MiniLM-L6-v2`), CPU inference.

**Rationale.** Ingestion embedding is offline, so hosted-API latency is irrelevant and
its rate limits are pure downside. Query-time embedding is a single short string —
CPU inference is a few milliseconds. Removes an API dependency, a rate limit, and a
key from the critical path.

**Trade-off accepted.** Slightly lower embedding quality than large hosted models;
immaterial for a corpus of this size. Adds ~100MB to the worker image.

**Outcome.** *[Fill in.]*

---

## 5. Repository layout

```
voice-twin/
├── CLAUDE.md                  # project context for Claude Code (root!)
├── README.md                  # public-facing; written last
├── ARCHITECTURE.md            # copy of the writeup for the repo
├── .env.example
├── .gitignore
├── docs/                      # this documentation set
├── agent/
│   ├── main.py                # worker entrypoint, AgentSession wiring
│   ├── twin_agent.py          # Agent subclass, instructions, tools
│   ├── retrieval.py           # pgvector search + threshold
│   ├── citations.py           # data channel publishing
│   ├── config.py              # env, thresholds, model IDs
│   └── prompts/
│       └── system_prompt.md   # editable, not buried in code
├── ingestion/
│   ├── ingest.py              # orchestrator
│   ├── loaders/               # pdf, markdown, github_mcp
│   ├── chunker.py
│   └── embedder.py
├── api/
│   └── main.py                # FastAPI token service
├── web/                       # React frontend
├── corpus/                    # source documents (gitignored if private)
└── tests/
```

---

## 6. Data model

Single table, `chunks`:

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `content` | text | The chunk text — this is what gets cited |
| `embedding` | vector(384) | Dimension must match your model |
| `source` | text | e.g. `resume.pdf`, `github:voice-twin` |
| `source_type` | text | `resume` \| `project` \| `writing` \| `profile` |
| `section` | text | Human-readable, shown on the citation card |
| `source_url` | text | Nullable; deep link when one exists |
| `content_hash` | text | For idempotent upserts |
| `ingested_at` | timestamptz | Freshness display |

Index: IVFFlat or HNSW on `embedding` for cosine distance.

---

## 7. Known boundaries (state these in the writeup)

- **Concurrency.** Gemini free tier is ~10 RPM. Fine for single-visitor demo; concurrent
  users need paid Gemini (~$0.30/M input tokens). The architecture doesn't change — only
  the billing flag.
- **Cold start.** Free-tier hosts sleep. Mitigated with keep-warm; production would use
  an always-on instance.
- **Corpus staleness.** Bounded by ingestion cadence, not unbounded.
- **Single tenant.** One person's twin. Multi-tenant would need corpus namespacing —
  a schema change, not an architecture change.
