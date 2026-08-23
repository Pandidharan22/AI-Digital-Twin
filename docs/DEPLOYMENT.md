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
GEMINI_MODEL=gemini-3.5-flash-lite

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
DATABASE_URL=

# GitHub (ingestion only)
GITHUB_TOKEN=
GITHUB_USERNAME=

# Retrieval tuning
RETRIEVAL_THRESHOLD=0.35
RETRIEVAL_TOP_K=5
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

**Re-verified (2026-08-23) — the GitHub Actions keep-warm cron is less
reliable than assumed, quantified for real.** `.github/workflows/
keep-warm.yml` is configured `*/10 * * * *`, but its actual last 14 runs
landed 15.4–47.4 minutes apart (median **25.8 min**, mean 26.3 min) —
**every single one** exceeded Render's own ~15-minute sleep threshold, not
just the "two runs" the 2026-08-22 entry flagged as an occasional anomaly.
GitHub Actions' `schedule` trigger is evidently deprioritizing this
low-activity repo's scheduled runs by a wide, consistent margin, not an
edge case.

Every individual ping still **succeeds** (100% success rate — the
100s-timeout-plus-retry fix from 2026-08-22 is doing its job), so the cron
itself isn't broken. But its actual *purpose* — keeping the gap under
Render's sleep threshold so a real visitor never lands on a cold instance —
is not being met: for roughly (gap − 15) minutes of every real gap, Render
has already gone to sleep and is just waiting for whichever comes first,
the next scheduled ping or an actual visitor. A visitor arriving in that
window pays the full 60–90s cold-start cost the keep-warm cron was
specifically built to prevent.

**Recommendation, not yet implemented:** this section's original Option 2
— an external uptime pinger (cron-job.org, UptimeRobot) — fires on its own
infrastructure's clock, not GitHub Actions' shared scheduler, and should
hit its configured interval far more reliably. Worth adding as a second,
more precise layer (or a replacement) rather than relying on GitHub Actions
alone for something this timing-sensitive; GitHub Actions remains perfectly
fine for the ingestion cron, where daily-ish timing doesn't matter. Setting
one up needs a new account on the owner's side — flagged as a concrete next
step, not done in this pass. See `docs/DEV_JOURNAL.md`'s 2026-08-23 entry
for the full data.

---

## 5. Free-tier limits and where they bite

| Service | Limit | Impact | If exceeded |
|---|---|---|---|
| LiveKit Build | 1,000 agent min/month | ~16 hrs conversation | Ample |
| Deepgram | $200 credit, no expiry | Thousands of minutes | Ample |
| Gemini Flash-Lite | ≥15 RPM (`gemini-3.5-flash-lite`, pinned, verified live 2026-08-21) | One turn = one request (grounded turns = two) | 429 → backoff |
| Supabase | 500MB DB, pauses after 7 days idle | Corpus is KB | Ping weekly |
| Vercel Hobby | 100GB bandwidth | Trivial | Ample |
| GitHub Actions | 2,000 min/month | Ingestion is minutes | Ample |

**The two real constraints:**

- **Gemini RPM.** The full-Flash tier this project ran on initially (5 RPM) was tight
  enough that a single visitor's greeting plus one grounded question tripped it in live
  Phase 3 testing (see `DEV_JOURNAL.md`, 2026-08-20) — no concurrency needed. Switched
  to the pinned `gemini-3.5-flash-lite` (≥15 RPM, verified live 2026-08-21) for more
  headroom; still worth budgeting for, since a grounded (tool-calling) turn costs two
  Gemini requests, not one. Exponential backoff (FR-7.1) is the plugin's own built-in
  retry; the spoken fallback (FR-7.2) is implemented in `agent/main.py`'s
  `session.on("error")` handler, so an exhausted retry budget reads as an apology, not
  a silent hang.
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
- [x] Link works from a device that never saw the project (2026-08-23,
      Android/Chrome real device test)
- [ ] Mobile Safari works — still open, 2026-08-23's test was Android, not iOS
- [x] Cellular network works (2026-08-23, real device, Wi-Fi off) — see
      `docs/TEST_PLAN.md` Sec4's U6 note for the one open item (occasional
      TTS audio glitching, not yet diagnosed)
- [x] Cold start under 15s (2026-08-23) — ~2-3s to welcome message on the
      real-device cellular test, well under target
- [ ] All four demo questions from `CITATION_SPEC.md` §7 behave correctly
- [ ] Sources render before speech
- [ ] Refusal shows the "no source" state

**Resilience**
- [x] Ingestion cron ran successfully at least once (2026-08-23) — confirmed
      via the GitHub Actions API, both the `Run ingestion` and `Validate
      corpus` steps green against the actual latest commit. Took six rounds
      of real, live fixes to get there (three secrets pasted with stray
      whitespace, a missing threshold config, a known gap that would have
      failed every run forever) — see `docs/DEV_JOURNAL.md`'s 2026-08-23
      entries for the full account.
- [ ] Idle 30 min then immediately usable — **re-verified 2026-08-23, not
      passing as designed**: the keep-warm cron's real gaps (median 25.8min,
      14/14 samples over Render's ~15min sleep threshold) mean a visitor can
      still land on a cold instance. See Sec4's 2026-08-23 note for the data
      and the recommended fix (an external uptime pinger).
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
