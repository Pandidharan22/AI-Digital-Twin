# PRD — Voice Twin

**Status:** Approved for build
**Owner:** [Your name]
**Target delivery:** 7 days from kickoff

---

## 1. Problem statement

A resume is static, one-directional, and answers only the questions its format allows.
A recruiter, collaborator, or client with a specific question — *"has he actually
shipped anything with WebRTC?"*, *"what was his role on that payments project?"* — has
no way to ask it without scheduling a call.

At the same time, an LLM chatbot trained loosely on a person's background is worse than
useless for this purpose, because it will confidently invent employment history. For a
hiring context, a fabricated claim is not a minor bug — it is a disqualifying one.

**Voice Twin solves this:** an always-available conversational agent that answers
questions about a person in real time, in natural speech, where **every factual claim
is grounded in and traceable to a real source document.**

---

## 2. Goals

| # | Goal | Why it matters |
|---|---|---|
| G1 | Natural real-time voice conversation | Text chat is a solved, unimpressive demo. Voice is the brief. |
| G2 | Every factual answer cited to a source | The explicit, graded requirement of the brief. |
| G3 | Refuses gracefully when it doesn't know | Hallucination in a hiring context is disqualifying. |
| G4 | Publicly accessible hosted link | The brief asks for "a link they can open and try". |
| G5 | Corpus stays fresh without manual work | Demonstrates systems thinking beyond a one-shot demo. |

### Non-goals (explicitly out of scope)

- Multi-user concurrency at scale (free tier is single-demo-user sized — this is a
  documented boundary, not an oversight).
- Voice cloning of the user's actual voice. Nice-to-have, not required by the brief.
- Multilingual support.
- Mobile native apps. Responsive web is sufficient.
- Any write action — the bot only reads and answers; it never posts, emails, or books.

---

## 3. Target users

**Primary: the evaluator.** Someone from Omnisavant opens the link, grants microphone
access, and asks 5–15 questions in a single session. They are specifically probing:
does it work, is it fast, are the citations real, and does it lie when pushed?

**Secondary: a recruiter or collaborator** encountering the link on a portfolio site.
Same interaction, less adversarial.

Design implication: **the first 20 seconds decide everything.** Connection must be
instant, mic permission must be obvious, and the first response must be fast and
correct.

---

## 4. User stories

| ID | As a… | I want to… | So that… |
|---|---|---|---|
| US-1 | visitor | click a link and start talking within seconds | I don't abandon before it loads |
| US-2 | visitor | ask about work history in natural speech | I get answers without reading a resume |
| US-3 | visitor | see which document each answer came from | I can trust it isn't inventing things |
| US-4 | visitor | interrupt the bot mid-sentence | the conversation feels human, not like an IVR |
| US-5 | visitor | ask something off-topic and get an honest "I don't have that" | I learn the bot's limits, and trust it more |
| US-6 | visitor | read a live transcript | I can follow along if audio is unclear |
| US-7 | owner | add a new project and have the bot know about it | I don't maintain the bot by hand forever |

---

## 5. Feature requirements

### P0 — Must ship. Project fails without these.

- **F1 Real-time voice I/O.** User speaks, bot hears, bot answers in speech, over
  WebRTC via LiveKit.
- **F2 Grounded answering.** Bot answers questions about the owner using retrieved
  content from the owner's real documents.
- **F3 Visible citations.** For every grounded answer, the UI displays the source
  document and section the answer drew from, synchronised with the spoken reply.
- **F4 Graceful refusal.** When retrieval returns nothing above the confidence
  threshold, the bot says it doesn't have that information. It never guesses.
- **F5 Hosted and public.** One URL, no install, works on desktop Chrome and mobile.
- **F6 Live transcript.** Both sides of the conversation render as text.

### P1 — Strongly expected. Ship unless time runs out.

- **F7 Barge-in.** User can interrupt the bot's speech and the bot stops immediately.
- **F8 Session memory.** Follow-ups like "what about before that?" resolve against
  earlier turns.
- **F9 Automated corpus refresh.** Scheduled ingestion pulls fresh GitHub data via the
  official GitHub MCP server without manual re-runs.
- **F10 Connection state UX.** Clear visual states: connecting, listening, thinking,
  speaking, error.

### P2 — Differentiators. Ship if ahead of schedule.

- **F11 Live-fact tool.** A separate real-time tool for facts that genuinely change
  (latest commit, current repo count), distinct from the static corpus.
- **F12 Latency instrumentation.** Measured and displayed first-audio latency.
- **F13 Suggested questions.** Starter prompts so a visitor isn't staring at a mic
  icon wondering what to say.

---

## 6. Success criteria

The project is done when all of these are true:

| # | Criterion | How it's measured |
|---|---|---|
| SC-1 | Time to first audio byte under 1.5s, median | Instrumented in `TEST_PLAN.md` |
| SC-2 | 100% of factual claims about the owner carry a visible source | Manual pass over the 20 test questions |
| SC-3 | 0 fabricated claims across the full test set | Manual review — any hallucination is a P0 bug |
| SC-4 | All 5 out-of-scope questions produce graceful refusals | `TEST_PLAN.md` refusal suite |
| SC-5 | Cold visitor reaches a working conversation in under 15s | Timed from link click on a clean browser |
| SC-6 | Works on mobile Safari and desktop Chrome | Manual device test |
| SC-7 | Total infrastructure cost is $0 | Billing dashboards |

---

## 7. What "done" looks like for the submission

Three artefacts go back to Omnisavant:

1. **A live link** that works when clicked, cold, on any device.
2. **A public repo** with clean structure, real README, and no secrets committed.
3. **A short architecture writeup** covering: why chained pipeline over speech-to-speech,
   how citations are enforced, measured latency, refusal design, and the RAG-vs-MCP
   decision. *This document is what separates this from a tutorial follow-along.*

---

## 8. Key risks

| Risk | Impact | Mitigation |
|---|---|---|
| Free-tier host cold start makes bot look broken | Fatal to evaluation | Keep-warm ping during eval window; see `DEPLOYMENT.md` |
| LLM ignores grounding rules and invents | Fails the core requirement | Threshold-gated retrieval + strict tool contract; see `CITATION_SPEC.md` |
| Latency exceeds conversational tolerance | Feels broken regardless of correctness | Stream every stage; pick fast-first-token model |
| Gemini free-tier 429 mid-demo | Visible failure | Exponential backoff + graceful spoken fallback |
| Building pipeline and RAG simultaneously | Nothing works, can't isolate cause | Phase gates in `BUILD_PLAN.md` — audio first, always |
