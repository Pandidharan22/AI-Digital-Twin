# Claude Code Prompt Playbook

Copy-paste prompts, phase by phase. Adapt the bracketed parts. Run them **in order**,
one at a time, verifying between each.

---

## How to prompt well on this project

**Five habits that matter more than the prompts themselves:**

1. **One phase per session.** Long sessions accumulate stale context and the agent
   starts contradicting earlier decisions. `/clear` between phases.
2. **Cite requirement IDs.** "Implement FR-3.3 per SRS" beats "add a threshold" — it
   gives the agent a spec to check itself against.
3. **Demand verification before implementation** on anything SDK-related. The LiveKit
   API changed in 1.0; an agent working from memory will produce `VoicePipelineAgent`
   code that doesn't exist anymore.
4. **Ask for a plan first on anything non-trivial.** Review the plan, then approve.
   Catching a wrong approach in a plan costs a minute; catching it in code costs an hour.
5. **Never accept "should work."** Ask it to run the thing.

**The single most important instruction to repeat:**
> Before writing any LiveKit code, read the actual installed version's API surface.
> Do not reproduce patterns from memory — the framework changed significantly in 1.0.

---

## Phase 0 — Scaffolding

### P0.1 — Project structure
```
Read docs/ARCHITECTURE.md and docs/SRS.md.

Set up the repository skeleton exactly as specified in ARCHITECTURE.md §5.
Create directories and placeholder files with docstrings describing each module's
responsibility. Do not implement logic yet.

Also create:
- .gitignore (Python, Node, .env, corpus/ if I mark it private)
- .env.example with every key from docs/DEPLOYMENT.md, values blank
- pyproject.toml using uv, Python 3.11+

Confirm .env is gitignored before we commit anything.
```

### P0.2 — Dependency verification
```
Before we write pipeline code, I need to know the actual API surface of the installed
LiveKit Agents SDK, not what you remember.

1. Install livekit-agents plus the deepgram, google, and silero plugins
2. Report the installed version
3. Read the package to determine: the current session/agent primitives, how to define
   function tools, how to publish to the data channel, and how a worker entrypoint is
   registered
4. Write findings to docs/SDK_NOTES.md with real import paths and signatures

Do not write project code yet. I want the API surface documented first.
```

*This prompt prevents the most common failure in this build. Do not skip it.*

---

## Phase 1 — Audio round-trip

### P1.1 — Minimal pipeline
```
Read docs/SDK_NOTES.md and docs/SRS.md FR-1 and FR-2.

Build a minimal working voice agent in agent/main.py:
- Deepgram Nova-3 streaming STT
- Gemini Flash LLM (free tier model ID)
- Deepgram Aura-2 TTS
- Silero VAD and the turn detector
- Trivial system prompt: a friendly assistant, no retrieval yet

Requirements:
- Config from environment variables via agent/config.py, no hardcoded keys
- Structured logging at each pipeline stage
- Spoken greeting on join per FR-1.6

Use the exact APIs from SDK_NOTES.md. Then tell me the command to run it in dev mode.
```

### P1.2 — Debugging (if needed)
```
The worker starts and registers but never joins the room when I connect from the
browser.

Here are the worker logs:
[paste]

Diagnose before changing code. Explain what should happen at each step of dispatch,
identify where it diverges, and only then propose a fix.
```

### P1.3 — Latency baseline
```
Add timing instrumentation per NFR-1: log elapsed ms for end-of-utterance → STT final,
STT final → LLM first token, LLM first token → first TTS audio byte, and total.

Write to structured logs with session and turn IDs. Then tell me how to read a summary
after a test conversation.
```

---

## Phase 2 — Ingestion

### P2.1 — Database schema
```
Read docs/ARCHITECTURE.md §6 and docs/DATA_INGESTION.md.

Generate SQL for Supabase:
1. Enable the vector extension
2. Create the chunks table exactly per the data model, vector(384)
3. Appropriate index for cosine similarity
4. A match_chunks(query_embedding, match_threshold, match_count) function returning
   rows with similarity scores
5. Unique constraint on content_hash for idempotent upserts

Save to ingestion/schema.sql and explain how to run it in the Supabase SQL editor.
```

### P2.2 — Chunking
```
Read docs/DATA_INGESTION.md §3 and §4.

Implement ingestion/chunker.py:
- Semantic boundary chunking per the table in §3 — NOT fixed token windows
- Contextual prefixing per §3 (embed prefixed, store clean)
- Enforce the size floor and ceiling
- Strip README boilerplate: badges, install blocks, license, TOC
- Emit full metadata per §4

Include unit tests with a sample resume section and a sample README, asserting that
chunks land on real boundaries and section labels are human-readable.
```

### P2.3 — Loaders and embedder
```
Implement:
- ingestion/loaders/pdf_loader.py — resume extraction preserving section structure
- ingestion/loaders/markdown_loader.py — local markdown
- ingestion/embedder.py — sentence-transformers BAAI/bge-small-en-v1.5, local CPU,
  batched, with the correct query prefix per the model card

Per ADR-006, embeddings are local. No hosted embedding API.
```

### P2.4 — GitHub MCP loader
```
Read docs/DATA_INGESTION.md §7.

Implement ingestion/loaders/github_mcp.py using the OFFICIAL GitHub MCP server.

Pull: repo list with metadata, README content per repo.
Filter out: forks, archived repos, repos with no README.
Auth via GITHUB_TOKEN.

Explain the MCP client setup clearly — I want to understand this part, not just run it.
Per SRS FR-6.7, do not implement any LinkedIn scraping.
```

### P2.5 — Orchestrator and validation
```
Implement ingestion/ingest.py tying loaders → chunker → embedder → Supabase upsert,
idempotent per DATA_INGESTION.md §6 including the stale-row deletion step.

Then implement ingestion/validate.py per §9: all structural assertions plus the 5
spot-check queries printing top results.

Run both against my corpus and show me the output.
```

---

## Phase 3 — Grounding and citations

### P3.1 — Retrieval with threshold
```
Read docs/CITATION_SPEC.md §3 and SRS FR-3.

Implement agent/retrieval.py:
- Embed the query with the same local model as ingestion
- Call match_chunks with RETRIEVAL_THRESHOLD (config, default 0.35) and TOP_K (4)
- Return EXACTLY the contract in CITATION_SPEC.md §3, including the no_match shape
  with its instruction field
- Threshold and top_k in config, not hardcoded

Include tests: a known in-corpus query returns match; a nonsense query returns no_match.
```

### P3.2 — Tool registration and prompt
```
Read docs/CITATION_SPEC.md §5.

1. Create agent/prompts/system_prompt.md with the full contract from §5, with my name
   substituted. Load it at runtime — do not hardcode it in Python.
2. Register search_my_background as a function tool on the Agent, using the exact
   pattern from docs/SDK_NOTES.md
3. Tool docstring must make clear it is REQUIRED before any factual claim

Do not implement citation publishing yet — that's the next step.
```

### P3.3 — Citation publishing
```
Read docs/CITATION_SPEC.md §4 and SRS FR-4.

Implement agent/citations.py:
- Build the payload exactly per the §4 schema
- Publish to the LiveKit data channel, topic "citations"
- CRITICAL per ADR-005: publish BEFORE returning chunks to the LLM, so cards render
  before speech begins
- Handle both match and no_match
- Stable turn_id correlating to the transcript turn

Show me exactly where in the retrieval flow this fires and confirm the ordering.
```

### P3.4 — Frontend citation rendering
```
Read docs/CITATION_SPEC.md §6 and SRS FR-4.3 to FR-4.6.

In the React app:
- Subscribe to the "citations" data channel topic
- Parse and render source cards: document, section, excerpt
- Bind cards to transcript turns via turn_id
- no_match → explicit "no documented source" chip AND clear previous cards (FR-4.6)
- Empty state before the first turn

Clean and readable. No raw JSON on screen.
```

### P3.5 — Threshold tuning
```
Read docs/TEST_PLAN.md.

Write tests/test_retrieval_suite.py running all in-corpus and out-of-corpus questions
against retrieval, reporting for each: top score, whether it matched, and whether that
was correct.

Run at thresholds 0.25, 0.30, 0.35, 0.40, 0.45 and produce a table so I can pick the
value with zero false accepts and minimum false refusals.
```

*Put the resulting table in your writeup. "I tuned the threshold empirically, here's the
data" is exactly the kind of thing that separates you from the pile.*

---

## Phase 4 — UX

### P4.1 — Connection states
```
Read SRS FR-5.

Implement agent state UI: connecting, listening, thinking, speaking, error.
Subscribe to the session's state events. Each state needs a distinct, immediately
readable visual. Never a silent unexplained state — FR-5.3.

Also implement the mic permission flow per FR-1.5: explain why before requesting.
```

### P4.2 — Transcript and suggestions
```
Implement the transcript panel per FR-5.1 — both sides, speaker-distinguished,
auto-scrolling, with the sources sidebar visually aligned to turns.

Add the four suggested questions from docs/CITATION_SPEC.md §7 as clickable chips
per FR-5.4.
```

### P4.3 — Design pass
```
Do a visual design pass on the frontend. Currently functional but plain.

Constraints:
- Must read as a polished product, not a dev tool
- Sources sidebar is the hero feature — make it feel substantial
- Mobile: sources become a collapsible sheet
- Accessible contrast, keyboard navigable

Show me the plan before implementing.
```

---

## Phase 5 — Deployment

### P5.1 — Containerisation
```
Read docs/DEPLOYMENT.md.

Create deployment config for:
1. Agent worker — long-running process, NOT a web service
2. FastAPI token service — web service with /health
3. Frontend — Vercel

Include Dockerfiles where needed, fly.toml if using Fly.io, and a checklist of env vars
per service. Note that the worker connects outbound, so it needs no inbound ports.
```

### P5.2 — Ingestion automation
```
Read docs/DATA_INGESTION.md §8.

Create .github/workflows/ingest.yml running ingestion daily on a schedule plus manual
dispatch. Secrets from repo settings. Log chunk counts and validation results in the
run summary so I can see failures without digging.
```

### P5.3 — Cold start hardening
```
Free-tier hosts sleep and a sleeping worker makes the bot look broken.

1. Audit where cold starts can occur across all three services
2. Implement keep-warm where appropriate
3. Add frontend handling so a slow first connection shows honest progress rather than
   appearing frozen

Explain each cold-start path and its mitigation.
```

---

## Phase 6 — Submission

### P6.1 — Test suite
```
Read docs/TEST_PLAN.md and SRS §6.

Implement the automated portions of the acceptance tests and give me a manual checklist
for the rest. Run the automated suite and report results.
```

### P6.2 — The writeup
```
Read docs/ARCHITECTURE.md.

Help me finish the submission writeup. The ADR Outcome fields are empty — here are my
real findings:
- Measured median first-audio latency: [X]ms
- Final threshold: [X], chosen because [Y]
- [other findings]

Produce a polished ARCHITECTURE.md for the repo root covering: system overview, the
chained-vs-S2S decision, how citations are structurally enforced, the RAG-vs-MCP
reasoning, measured latency, refusal design, and known scaling boundaries.

Technical and specific. This is read by engineers evaluating my judgement.
```

### P6.3 — Public README
```
Write the public README.md: one-line description, live link, screenshot placeholder,
what makes it interesting (citation architecture), stack table, local setup that works
from a clean clone, architecture diagram, and honest known limitations.

Confident but not overselling. Assume a skeptical engineer is reading.
```

---

## Debugging prompt templates

**When something is broken:**
```
[Component] is doing [X], expected [Y].

Symptoms: [what you see]
Logs: [paste]
Already tried: [list]

Diagnose before changing code. Walk through what should happen at each step, identify
where it diverges, and explain the root cause. Then propose a fix.
```

**When it hallucinates:**
```
Asked "[question]" and it answered "[fabricated answer]" — that is not in my corpus.

Per docs/CITATION_SPEC.md §2 this should be blocked at four layers. Trace which layer
failed: did retrieval return chunks it shouldn't have, did the threshold not apply, or
did the model ignore the prompt contract?

Show me the actual retrieval output for that query before proposing a fix.
```

**When latency is bad:**
```
First-audio latency is [X]ms, target is under 1500ms per NFR-1.1.

Use the stage timings from P1.3 to identify the dominant stage. Do not guess — show me
the numbers per stage, then propose targeted optimisations for the worst one.
```
