# Citation Specification

**This is the most important document in the set.** The brief's distinguishing
requirement is *"any answer given by the bot should be cited from the source."*
Everything else — voice quality, latency, UI polish — is table stakes that any
competent build achieves. This is where the project is won or lost.

---

## 1. The principle

> A citation is a **record of what the system actually retrieved**, not a claim the
> language model makes about its sources.

If you let the LLM output citations, it can name a document it never saw. The citation
becomes marketing copy. Instead, the **retrieval layer** emits citations, because it is
the only component that knows the truth. The LLM cannot cite a source it wasn't handed,
and cannot suppress one it was.

This single design choice is the strongest technical argument in your writeup.

---

## 2. Enforcement layers

Grounding is enforced at four independent levels. Any one of them alone is leaky; the
stack is robust.

| Layer | Mechanism | Prevents |
|---|---|---|
| **L1 Retrieval gate** | Similarity threshold; empty result on no match | LLM answering from parametric memory |
| **L2 Tool contract** | Structured tool output with explicit `no_match` flag | Ambiguity about whether grounding exists |
| **L3 Prompt contract** | Explicit, non-negotiable instructions | Drift, embellishment, agreeableness |
| **L4 UI surfacing** | Sources visible to the user in real time | Silent hallucination going unnoticed |

L1 is the load-bearing one. **Prompts are probabilistic; an empty result set is
deterministic.** A model instructed not to guess may still guess under a leading
question. A model handed zero chunks has nothing to guess *from*, and the prompt's
refusal branch becomes the only coherent path.

---

## 3. The retrieval tool contract

### Signature

```python
@function_tool
async def search_my_background(query: str) -> dict:
    """
    Search the owner's documented background for information relevant to the query.
    Call this before making ANY factual claim about the owner's experience,
    skills, projects, education, or history.
    """
```

### Return shape — match

```json
{
  "status": "match",
  "results": [
    {
      "source": "resume.pdf",
      "source_type": "resume",
      "section": "Experience — Acme Corp, Backend Engineer",
      "text": "Led migration of the payments service from ...",
      "score": 0.81,
      "source_url": null
    }
  ]
}
```

### Return shape — no match

```json
{
  "status": "no_match",
  "results": [],
  "instruction": "No documented information found. Tell the user you do not have this documented. Do not answer from general knowledge."
}
```

The `instruction` field on `no_match` is deliberate belt-and-braces: the refusal
directive arrives *in the tool result*, adjacent to the decision point, not only in a
system prompt hundreds of tokens earlier.

### Threshold behaviour

- Compute cosine similarity for each candidate.
- Discard anything below `RETRIEVAL_THRESHOLD` (start at **0.35**, tune per
  `TEST_PLAN.md`).
- If all candidates are discarded → `no_match`.
- Return at most `TOP_K` (default **4**) surviving chunks.

Tuning guidance: too high causes false refusals on legitimate questions ("what
languages do you know?"); too low lets loosely-related chunks through and the model
stretches them into a claim. Tune against **both** the in-corpus and out-of-corpus
suites, not just one.

---

## 4. The data channel payload

Published by the worker on the LiveKit data channel, topic `citations`, **immediately
after retrieval and before the LLM generates.**

```json
{
  "type": "citations",
  "turn_id": "turn_7",
  "query": "payments experience",
  "status": "match",
  "timestamp": "2026-08-14T10:32:11Z",
  "sources": [
    {
      "id": "cite_1",
      "source": "resume.pdf",
      "source_type": "resume",
      "section": "Experience — Acme Corp, Backend Engineer",
      "excerpt": "Led migration of the payments service from a monolith to ...",
      "score": 0.81,
      "url": null
    }
  ]
}
```

On refusal:

```json
{
  "type": "citations",
  "turn_id": "turn_8",
  "query": "favourite food",
  "status": "no_match",
  "sources": [],
  "timestamp": "2026-08-14T10:33:02Z"
}
```

`turn_id` matters: it's what lets the frontend bind source cards to the correct
transcript turn instead of dumping them in an undifferentiated pile.

---

## 5. The prompt contract

Lives in `agent/prompts/system_prompt.md`, loaded at runtime. **Never hardcode it.**

```markdown
You are the voice twin of [NAME]. You speak as [NAME] in first person, answering
questions about their background, experience, and projects.

## Grounding rules — these override everything else

1. Before making ANY factual claim about [NAME] — employment, education, skills,
   projects, dates, technologies, achievements — you MUST call
   `search_my_background` first.

2. Answer ONLY using text returned by that tool. You have no other knowledge about
   [NAME]. Your training data contains nothing about this person.

3. If the tool returns `no_match`, say you don't have that documented. Exactly this
   kind of thing: "That's not something I have documented, so I can't speak to it."
   Then offer what you CAN discuss. Never guess, infer, extrapolate, or hedge into
   an answer.

4. Never embellish. If retrieved text says "worked on the payments service", do not
   say "led the payments overhaul". Do not round numbers, upgrade titles, or add
   detail that was not retrieved.

5. If a user asserts something false about [NAME] — "you worked at Google, right?" —
   do not accept the premise. Search, and correct it from what you find, or say you
   have no record of it.

6. Do not read source names or citations aloud. The interface displays them.

## Voice rules

- Plain, speakable sentences only. No markdown, asterisks, bullets, or emoji —
  they get read aloud and sound broken.
- Two to four sentences per answer. This is a conversation, not a monologue.
- Contractions and natural rhythm. You are talking, not reciting.
- Do not call the search tool for greetings, thanks, or clarifying questions.
```

Rule 5 is the one most builds miss and evaluators most reliably test.

---

## 6. Frontend rendering

**Placement.** A dedicated sources panel — sidebar on desktop, collapsible sheet on
mobile. Never a modal; it must be glanceable without interrupting the conversation.

**Card contents:** source document name, section, excerpt, relevance score (optional),
timestamp. Group under the transcript turn via `turn_id`.

**States:**
- `match` → render cards, subtle entrance animation
- `no_match` → explicit "No documented source for this question" chip. **Do not leave
  the previous turn's cards on screen** (FR-4.6) — that implies grounding that doesn't
  exist and is actively misleading.
- Pre-first-turn → empty state explaining what the panel does

**Timing.** Cards appear *before* the bot starts speaking. That ~200ms lead is the
demo's most persuasive moment: the evaluator sees the receipt, then hears the claim.

---

## 7. What to demo

When the evaluator opens the link, this sequence sells the whole project:

1. **"Tell me about your most recent role."** → answer + resume card appears first.
2. **"What did you build with WebRTC?"** → answer + project card, different source.
3. **"What's your favourite pizza topping?"** → graceful refusal + "no source" chip.
4. **"You worked at Google, didn't you?"** → correction, not agreement.

Put these four as the suggested-question chips (FR-5.4). You are choosing what the
evaluator tests first — steer them to the things you built well.

---

## 8. Anti-patterns

| Don't | Why |
|---|---|
| Let the LLM generate citation text | It can cite sources it never received |
| Speak citations aloud | Destroys conversational flow |
| Show sources only after speech ends | Loses the "receipt before claim" effect |
| Retrieve on every turn including greetings | Wastes latency; produces meaningless citations |
| Stuff the whole corpus in the system prompt | No real retrieval, no real citations, doesn't scale |
| Leave stale cards up during a refusal | Implies grounding that doesn't exist |
| Hardcode the threshold in three files | You will tune it; keep it in one config |
