# Deployment Guide

The brief asks for *"a link they can open and try."* That link working, cold, on someone
else's device, is a hard requirement — not a finishing touch.

---

## 1. Environment variables

`.env.example` — commit this with blank values. Never commit `.env`.

```bash
# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

# Deepgram — ONE key covers both STT and TTS
DEEPGRAM_API_KEY=

# Google Gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-flash-latest

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
DATABASE_URL=

# GitHub (ingestion only)
GITHUB_TOKEN=
GITHUB_USERNAME=

# Retrieval tuning
RETRIEVAL_THRESHOLD=0.35
RETRIEVAL_TOP_K=4
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# Identity
OWNER_NAME=
```

**Distribution by service:**

| Variable | Worker | Token API | Frontend | Ingestion |
|---|:-:|:-:|:-:|:-:|
| `LIVEKIT_URL` | ✅ | ✅ | ✅ (public) | |
| `LIVEKIT_API_KEY/SECRET` | ✅ | ✅ | ❌ **never** | |
| `DEEPGRAM_API_KEY` | ✅ | | | |
| `GEMINI_API_KEY` | ✅ | | | |
| `SUPABASE_*` | ✅ | | | ✅ |
| `GITHUB_TOKEN` | | | | ✅ |

The frontend gets **only** the public LiveKit URL. Everything else stays server-side.

---

## 2. Service topology

| Service | Type | Host | Why |
|---|---|---|---|
| Agent Worker | Long-running process | Fly.io | Persistent, outbound-only |
| Token API | Web service | Fly.io / Render | Stateless HTTP |
| Frontend | Static SPA | Vercel | Free, fast, global |
| Vector store | Managed Postgres | Supabase | pgvector included |
| Ingestion | Scheduled job | GitHub Actions | Free, visible history |

**The worker is not a web service.** It connects *outbound* to LiveKit Cloud and waits
for dispatch. No inbound ports, no public IP, no tunnelling. Deploying it as a web
service is a common mistake — platforms will health-check a port it never opens and
kill it.

That same property means **it runs fine from your laptop** for a live demo. Keep that as
your fallback.

---

## 3. Deployment order

Deploy bottom-up; each layer depends on the one below.

1. **Supabase** — project, `vector` extension, schema, `match_chunks` function. Run
   ingestion against production. Verify chunk count in the dashboard.
2. **Token API** — deploy, then `curl` the `/health` and `/token` endpoints. Confirm a
   valid token comes back before touching anything else.
3. **Agent worker** — deploy as a process/worker. Watch logs for successful registration
   with LiveKit.
4. **Frontend** — deploy to Vercel with the production token API URL. Then open the link
   in a **fresh browser profile**.
5. **Ingestion cron** — GitHub Actions with repo secrets. Trigger manually once to verify.

---

## 4. Cold starts — the thing that sinks demos

Free tiers sleep. A sleeping worker means the visitor connects, waits, hears nothing,
and concludes your project is broken. It is the most common cause of a working project
evaluating badly.

**Where cold starts hide:**

| Service | Symptom | Mitigation |
|---|---|---|
| Token API | First request 10–30s | Cron ping `/health` every 10 min |
| Agent worker | Connects, agent never joins | Keep process always-on; ping if it exposes a port |
| Supabase | First query slow | Usually fine; warmed by worker startup |
| Frontend | None | Static, always fast |

**Mitigations, in order of preference:**

1. **Always-on worker.** Fly.io's free allowance can run a small machine continuously.
   Configure it not to auto-stop. Best option.
2. **External keep-warm.** A free uptime pinger (cron-job.org, UptimeRobot) hitting
   `/health` every 5–10 minutes.
3. **Pay a few dollars for the evaluation window.** Not free-tier-pure, but $5 to avoid
   failing a job evaluation is rational. You can scale back after.
4. **Honest frontend handling.** If the agent hasn't joined within 5 seconds, show
   "waking up the agent, this takes a few seconds" rather than a frozen screen. Never
   let silence read as failure.

**Mandatory test:** after deploying, leave everything idle 30+ minutes. Then open the
link on a phone, on cellular, in a browser that has never seen the site. Time it. If it
exceeds 15 seconds, fix it before submitting.

---

## 5. Free-tier limits and where they bite

| Service | Limit | Impact | If exceeded |
|---|---|---|---|
| LiveKit Build | 1,000 agent min/month | ~16 hrs conversation | Ample |
| Deepgram | $200 credit, no expiry | Thousands of minutes | Ample |
| Gemini Flash | ~10 RPM, ~250 RPD | One turn = one request | 429 → backoff |
| Supabase | 500MB DB, pauses after 7 days idle | Corpus is KB | Ping weekly |
| Vercel Hobby | 100GB bandwidth | Trivial | Ample |
| GitHub Actions | 2,000 min/month | Ingestion is minutes | Ample |

**The two real constraints:**

- **Gemini RPM.** Fine for one visitor. Two people talking simultaneously can trip it.
  Implement exponential backoff with jitter (FR-7.1) and a spoken fallback (FR-7.2).
- **Supabase idle pause.** Free projects pause after ~7 days of inactivity. Your daily
  ingestion cron incidentally prevents this — a nice side effect worth noting.

**State the scaling boundary in your writeup.** "This handles single-user demo load;
concurrent users need paid Gemini at roughly $0.30 per million input tokens, with no
architecture change" is a stronger answer than pretending the limit isn't there.

---

## 6. Pre-submission checklist

**Security**
- [ ] No secrets in the frontend bundle (open devtools, search it)
- [ ] No secrets in git history (`git log -p | grep -i` for key patterns)
- [ ] `.env` gitignored; `.env.example` has blanks only
- [ ] Token endpoint rate-limited (NFR-3.4)
- [ ] Tokens expire ≤ 15 min (FR-1.3)

**Functionality**
- [ ] Link works from a device that never saw the project
- [ ] Mobile Safari works
- [ ] Cellular network works
- [ ] Cold start under 15s
- [ ] All four demo questions from `CITATION_SPEC.md` §7 behave correctly
- [ ] Sources render before speech
- [ ] Refusal shows the "no source" state

**Resilience**
- [ ] Ingestion cron ran successfully at least once
- [ ] Idle 30 min then immediately usable
- [ ] Mic-denied path shows a helpful message
- [ ] Rate limit produces a spoken fallback, not silence

**Submission**
- [ ] Repo public, clean history
- [ ] README setup works from a clean clone
- [ ] `ARCHITECTURE.md` complete with real measured numbers
- [ ] Screen recording as backup

---

## 7. Demo-day contingencies

| If | Do |
|---|---|
| Hosted worker dies | Run the worker locally — outbound connection means it just works |
| Gemini rate-limits | Have a paid key ready as a swap-in env var |
| Supabase paused | Open the dashboard to wake it before the session |
| Everything fails | Send the screen recording, be honest, offer a live call |

Record the 60-second demo video **before** you need it. It costs ten minutes and it is
the difference between "the link was down" and "here's it working, plus here's the link."
