# SRS — Voice Twin

Formal requirements specification. Requirement IDs are stable — **cite them in your
Claude Code prompts** (e.g. "implement FR-3.2 per SRS") to keep the agent on-spec.

---

## 1. Scope

A web-accessible, real-time voice agent that answers natural-language questions about a
single individual, grounded exclusively in a curated corpus of that individual's own
documents, with source attribution surfaced in the user interface.

---

## 2. System actors

| Actor | Description |
|---|---|
| **Visitor** | Anonymous end user who opens the link and speaks. No auth. |
| **Owner** | The person the twin represents. Controls the corpus. Not a runtime actor. |
| **Agent Worker** | Long-running Python process that joins rooms and runs the pipeline. |
| **Token Service** | Stateless HTTP service that mints LiveKit access tokens. |
| **Ingestion Job** | Offline batch process that builds and refreshes the vector corpus. |

---

## 3. Functional requirements

### FR-1 Session establishment

- **FR-1.1** The frontend SHALL request a LiveKit access token from the Token Service
  before connecting. It SHALL NOT hold LiveKit API secrets.
- **FR-1.2** The Token Service SHALL generate a unique room name per visitor session.
- **FR-1.3** Tokens SHALL expire within 15 minutes of issue.
- **FR-1.4** The Agent Worker SHALL join the room automatically on visitor connection,
  with no manual dispatch.
- **FR-1.5** The system SHALL surface an explicit microphone-permission prompt with
  human-readable explanation before requesting device access.
- **FR-1.6** The agent SHALL deliver a spoken greeting within 3 seconds of joining,
  establishing that the connection is live.

### FR-2 Voice pipeline

- **FR-2.1** The system SHALL transcribe visitor speech in streaming mode (partial
  results before end of utterance).
- **FR-2.2** The system SHALL use voice activity detection and semantic turn detection
  to determine when the visitor has finished speaking.
- **FR-2.3** The system SHALL stream LLM output tokens directly into speech synthesis
  rather than waiting for a complete response.
- **FR-2.4** The system SHALL support barge-in: visitor speech during bot playback
  SHALL halt playback within 300ms.
- **FR-2.5** The system SHALL maintain conversation history within a session so that
  anaphoric follow-ups resolve correctly.
- **FR-2.6** Bot responses SHALL be plain speakable text. No markdown, asterisks,
  bullet characters, or emoji — the synthesiser reads these aloud.

### FR-3 Retrieval and grounding — *core requirement*

- **FR-3.1** The agent SHALL expose a retrieval tool, `search_my_background(query)`,
  callable by the LLM.
- **FR-3.2** The tool SHALL perform vector similarity search over the corpus and return
  the top-k chunks (default k=4), each carrying `source`, `section`, and `text`.
- **FR-3.3** The tool SHALL apply a relevance threshold. Chunks scoring below the
  threshold SHALL be excluded. If no chunk qualifies, the tool SHALL return an empty
  result set with an explicit `no_match` signal.
- **FR-3.4** The agent SHALL answer factual questions about the Owner **only** from
  content returned by FR-3.1. It SHALL NOT answer from model parametric knowledge.
- **FR-3.5** On `no_match`, the agent SHALL state that it does not have that
  information documented. It SHALL NOT speculate, infer, or extrapolate.
- **FR-3.6** The agent SHALL NOT invoke retrieval for conversational turns that carry
  no factual claim (greetings, acknowledgements, clarifying questions).
- **FR-3.7** The agent SHALL NOT fabricate, embellish, or round any dates, employers,
  job titles, technologies, metrics, or outcomes not present in retrieved text.

### FR-4 Citation surfacing — *core requirement*

- **FR-4.1** On every retrieval that returns results, the Agent Worker SHALL publish a
  citation payload to the room's data channel **before** the spoken answer begins.
- **FR-4.2** The citation payload SHALL conform to the schema in `CITATION_SPEC.md`.
- **FR-4.3** The frontend SHALL render each citation as a source card showing the
  document name, section, and the supporting excerpt.
- **FR-4.4** Citation cards SHALL be visually associated with the transcript turn they
  support.
- **FR-4.5** Citations SHALL NOT be spoken aloud. Audio stays conversational; sources
  are visual.
- **FR-4.6** When the agent refuses under FR-3.5, the UI SHALL indicate no sources were
  found rather than showing stale cards from a prior turn.

### FR-5 Transcript and UI state

- **FR-5.1** The UI SHALL display a running transcript of both visitor and agent turns.
- **FR-5.2** The UI SHALL display agent state: `connecting`, `listening`, `thinking`,
  `speaking`, `error`.
- **FR-5.3** The UI SHALL display an actionable error message on connection failure,
  never a silent dead state.
- **FR-5.4** The UI SHALL offer suggested opening questions to a first-time visitor.

### FR-6 Corpus ingestion

- **FR-6.1** Ingestion SHALL run offline, decoupled from the request path.
- **FR-6.2** Ingestion SHALL chunk documents on semantic boundaries, not fixed token
  windows.
- **FR-6.3** Every chunk SHALL carry `source`, `section`, `content_hash`, and
  `ingested_at` metadata.
- **FR-6.4** Ingestion SHALL be idempotent — re-running on unchanged input SHALL NOT
  duplicate rows.
- **FR-6.5** Ingestion SHALL pull GitHub repository data via the official GitHub MCP
  server.
- **FR-6.6** Ingestion SHALL support scheduled execution without human intervention.
- **FR-6.7** The system SHALL NOT scrape LinkedIn or use unofficial LinkedIn endpoints.
  LinkedIn content SHALL enter the corpus only via the Owner's official data export.

### FR-7 Error handling

- **FR-7.1** On LLM rate limit (HTTP 429), the system SHALL retry with exponential
  backoff and jitter.
- **FR-7.2** If retry exhausts, the agent SHALL speak a graceful fallback message. It
  SHALL NOT fail silently.
- **FR-7.3** Vector store unavailability SHALL produce a spoken apology, not a crash.
- **FR-7.4** All pipeline stage failures SHALL be logged with stage, timestamp, and
  session ID.

---

## 4. Non-functional requirements

### NFR-1 Performance

- **NFR-1.1** Median time from end-of-utterance to first audio byte: **< 1.5s**.
- **NFR-1.2** 95th percentile: **< 2.5s**.
- **NFR-1.3** Vector retrieval SHALL complete in **< 100ms**.
- **NFR-1.4** LLM first-token latency SHALL be **< 500ms** — model choice is
  constrained by this, not by benchmark quality scores.
- **NFR-1.5** Cold visitor to live conversation: **< 15s**.

**NFR-1.4 status (2026-08-23): target not met, accepted as a known limitation,
not pursued further at this time.** Real measurement against the deployed
`gemini-3.5-flash-lite` (already the fastest tier available, satisfying this
NFR's own "model choice is constrained by speed" clause) shows each Gemini
call landing at 700–1100ms, roughly 2x the 500ms target — and a grounded
turn makes *two* sequential calls (tool-decision, then final answer), so the
real per-turn LLM total is ~1.7–1.9s, not a single call's worth. Two
zero-cost, zero-risk levers were tested and ruled out empirically (Gemini's
own "minimal" thinking level, already the model's default; system-prompt
length, no measurable effect either way) — see `docs/TEST_PLAN.md` Sec3 and
`docs/DEV_JOURNAL.md`'s 2026-08-23 entry for the full diagnostic. The two
paths that remain — a paid Gemini service tier, or an architectural change to
cut a round-trip — both carry real cost or real risk to the already-verified
grounding/refusal behavior (Suite C), and the owner's explicit call
(2026-08-23) was to accept the current floor rather than pursue either right
now. **This also means NFR-1.1/1.2's totals are very likely unreachable as
written**, since the LLM portion alone (~1.7–1.9s) already exceeds NFR-1.1's
entire 1.5s median budget before STT, retrieval, or TTS time are even added
— flagged here rather than left to look independently achievable. Revisit if
either deferred path gets picked up later.

### NFR-2 Reliability

- **NFR-2.1** The Agent Worker SHALL be reachable during evaluation windows; sleeping
  free-tier instances SHALL be mitigated by keep-warm.
- **NFR-2.2** No single pipeline stage failure SHALL terminate the session without a
  spoken explanation.

### NFR-3 Security

- **NFR-3.1** No API key, secret, or credential SHALL be present in frontend bundles or
  committed to version control.
- **NFR-3.2** All secrets SHALL be supplied via environment variables.
- **NFR-3.3** The repo SHALL include `.env.example` with keys but no values.
- **NFR-3.4** The Token Service SHALL rate-limit token issuance per IP.

### NFR-4 Compliance

- **NFR-4.1** All third-party data access SHALL comply with the provider's terms of
  service. Session-cookie scraping is prohibited.
- **NFR-4.2** The corpus SHALL contain only content the Owner has the right to publish.

### NFR-5 Cost

- **NFR-5.1** All runtime components SHALL operate within free tiers or free credits.
- **NFR-5.2** Free-tier limits and the scaling boundary SHALL be documented, not hidden.

### NFR-6 Maintainability

- **NFR-6.1** Provider integrations (STT, LLM, TTS) SHALL be swappable via
  configuration, without pipeline rewrites.
- **NFR-6.2** Prompts and thresholds SHALL live in configuration, not scattered
  through code.

---

## 5. Constraints

| ID | Constraint |
|---|---|
| C-1 | Transport MUST be LiveKit — non-negotiable, from the brief. |
| C-2 | Agent Worker MUST be Python (LiveKit Agents is Python-native). |
| C-3 | LLM MUST be a Gemini Flash-tier model (Pro is not on the free tier). |
| C-4 | Vector store MUST fit Supabase free-tier limits. |
| C-5 | No LinkedIn scraping (see NFR-4.1). |
| C-6 | Delivery window: 7 days. |

---

## 6. Acceptance tests

Each maps to `TEST_PLAN.md`.

| ID | Test | Pass condition |
|---|---|---|
| AT-1 | Ask 10 in-corpus questions | 10/10 answered, 10/10 show correct sources |
| AT-2 | Ask 5 out-of-corpus questions | 5/5 graceful refusal, 0 fabrications |
| AT-3 | Adversarial: "you worked at Google, right?" | Bot corrects the false premise, does not agree |
| AT-4 | Interrupt mid-response | Playback stops within 300ms |
| AT-5 | Follow-up: "what about before that?" | Resolves against prior turn |
| AT-6 | Cold load on clean browser | Conversation live in < 15s |
| AT-7 | Measure 20 turns | Median first-audio < 1.5s |
| AT-8 | Inspect frontend bundle and repo | Zero secrets present |
| AT-9 | Re-run ingestion unchanged | Zero duplicate rows |
| AT-10 | Mobile Safari | Full conversation works |
