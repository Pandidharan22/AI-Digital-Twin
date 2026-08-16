# Voice Twin — Project Documentation Set

A cited, real-time voice agent that answers questions about **you**, grounded in your
own documents, with every factual claim traceable to a source.

Built for the Omnisavant.ai brief: *"Build your digital twin voice bot that answers
questions about yourself using LiveKit. Any answer given by the bot should be cited
from the source (resume, projects etc). Looking for: hosted working bot, UX."*

---

## How to use this documentation set

1. Create your project directory (e.g. `voice-twin/`).
2. Copy **all** these `.md` files into `voice-twin/docs/`.
3. Copy `CLAUDE.md` into the **project root** (not `docs/`) — Claude Code reads it
   automatically on every session and it keeps the agent on-spec.
4. Open Claude Code in the project root.
5. Work through `BUILD_PLAN.md` phase by phase, using the prompts in
   `CLAUDE_CODE_PROMPTS.md`.

**Do not** paste all docs into one giant prompt. Claude Code performs far better with
one phase at a time and a verification checkpoint between each.

---

## Document index

| File | What it's for | When you read it |
|---|---|---|
| `PRD.md` | Product requirements — who this is for, what it must do, success criteria | Before you start; skim before every phase |
| `SRS.md` | Formal software requirements — numbered functional/non-functional requirements | Reference when writing prompts; cite requirement IDs |
| `ARCHITECTURE.md` | System design, component boundaries, ADRs with rationale | Before Phase 1; the source of your writeup |
| `CITATION_SPEC.md` | The citation contract — the heart of the project | Before Phase 3 (most important doc) |
| `DATA_INGESTION.md` | Corpus sources, chunking, metadata, MCP freshness pipeline | Before Phase 2 |
| `BUILD_PLAN.md` | 7-day step-by-step with checkpoints and exit criteria | Every day |
| `CLAUDE_CODE_PROMPTS.md` | Copy-paste prompt playbook, phase by phase | Every prompt you write |
| `DEPLOYMENT.md` | Hosting, env vars, cold starts, the "hosted link" requirement | Phase 6 |
| `TEST_PLAN.md` | Test questions, refusal tests, latency measurement | Phase 5 onward |
| `CLAUDE.md` | Project context file — **goes in project root** | Never edit mid-build without reason |
| `DEV_JOURNAL.md` | Dated log of every verified step: what changed, why, and the concepts behind it | After every step, before moving to the next |

---

## The one-paragraph summary of the system

A React frontend connects a user to a **LiveKit Cloud** room. A Python **agent worker**
joins the same room, transcribes the user's speech with **Deepgram Nova-3**, and passes
the text to **Gemini Flash**. The LLM has one primary tool, `search_my_background`,
which runs a vector similarity search over a curated corpus of the user's documents
stored in **Supabase pgvector**. Retrieved chunks carry source metadata; those sources
are pushed to the frontend over LiveKit's data channel **before** the answer is spoken,
so the UI displays the citation alongside the spoken claim. The reply is synthesised by
**Deepgram Aura-2** and streamed back into the room. A separate offline ingestion
pipeline — refreshed on a schedule via the **official GitHub MCP server** — keeps the
corpus current without paying any latency cost at query time.

---

## Cost

Every component runs on a free tier or free credit. **Total out of pocket: $0.**
See `DEPLOYMENT.md` for the limits of each and where they bite.

---

## Ground rules for this build

- **Verify the SDK surface before writing pipeline code.** The LiveKit Agents API
  changed significantly in 1.0 (`AgentSession` replaced `VoicePipelineAgent`). Any
  tutorial older than that is wrong. Always check the installed version's docs first.
- **Ship a working narrow thing before a broken wide thing.** Audio round-trip first,
  intelligence second.
- **The citation mechanism is the graded feature.** If you run out of time, cut voice
  polish before you cut citations.
- **Write down decisions as you make them.** `ARCHITECTURE.md` has an ADR section;
  filling it in as you go is what turns this into a portfolio piece.
