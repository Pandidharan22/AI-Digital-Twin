# Data Ingestion Specification

Your bot's quality is capped by your corpus quality. A perfect pipeline over a bad
corpus produces a bot that confidently cites garbage. Budget real time for this.

---

## 1. Corpus sources

| Source | Access method | Refresh | Priority |
|---|---|---|---|
| Resume / CV (PDF) | Local file | Manual, rare | **P0** |
| Project READMEs | GitHub MCP | Automated, daily | **P0** |
| Personal bio / about | Local markdown | Manual | **P0** |
| LinkedIn profile | **Official data export only** | Manual, quarterly | P1 |
| Blog posts / writing | Local markdown or RSS | Automated | P1 |
| Repo metadata (stars, languages, dates) | GitHub MCP | Automated, daily | P1 |
| Talks, certifications | Local markdown | Manual | P2 |

### On LinkedIn — read this before you build

There is **no official LinkedIn MCP server**. Every third-party option either scrapes
with a session cookie or uses unofficial endpoints; both violate LinkedIn's User
Agreement and risk account restriction.

**Do this instead:** LinkedIn Settings → Data Privacy → Get a copy of your data.
Download the archive, drop the relevant files into `corpus/linkedin/`, ingest as local
files. Same content, zero risk, and you keep a clean ToS story.

**Say this in your writeup.** "I evaluated community LinkedIn MCP servers and rejected
them — they rely on cookie-based session automation that violates LinkedIn's terms, so
I used the official data export instead" is a strong signal. Evaluators notice
candidates who consider terms of service.

---

## 2. Handwritten context — the highest-leverage hour of this project

Your resume is written for ATS keyword matching. It is a terrible conversational
source. Before ingesting anything, write **`corpus/context.md`** by hand: 1,000–2,000
words answering the questions people actually ask, in the voice you want the bot to use.

Cover: what you're working on now, why you chose your field, your strongest project and
what was actually hard about it, technologies you know well versus have touched once,
what you're looking for, notable failures and what they taught you, how you learn.

Write it in first person, conversationally. This file will source more good answers
than your resume will, because it contains the things a resume has no room for. An hour
here beats a day of pipeline tuning.

---

## 3. Chunking strategy

**Chunk on semantic boundaries, never fixed token windows.** A citation must point to a
*coherent unit* — "Experience — Acme Corp, Backend Engineer" is a real citation;
"characters 1400–1900 of resume.pdf" is not.

| Document type | Chunk boundary | Target size |
|---|---|---|
| Resume | One role, one education entry, one skills block | 100–300 tokens |
| README | One markdown `##` section | 150–400 tokens |
| `context.md` | One topic/question block | 150–400 tokens |
| Blog post | One `##` section, or whole post if short | 200–500 tokens |
| LinkedIn export | One position, one recommendation | 100–300 tokens |

**Rules:**
- Never split mid-sentence.
- If a section exceeds ~500 tokens, split on paragraph and repeat the parent heading in
  each part's `section` metadata so the citation stays meaningful.
- Discard chunks under ~40 tokens — they're headers or noise and pollute retrieval.
- **Strip README boilerplate**: badges, install instructions, license blocks, tables of
  contents. These match many queries weakly and crowd out real content. This filtering
  step measurably improves retrieval.

### Contextual prefixing (do this)

Prepend a one-line context header to each chunk's embedded text:

```
[Source: resume.pdf | Section: Experience — Acme Corp, Backend Engineer]
Led migration of the payments service from ...
```

Embed the prefixed version; store and cite the clean version. This meaningfully
improves retrieval on short queries, because an isolated bullet like "Reduced p99
latency by 40%" has no signal about *where* it happened until you give it some.

---

## 4. Metadata schema

Every chunk carries:

| Field | Required | Example | Purpose |
|---|---|---|---|
| `source` | ✅ | `resume.pdf` | Citation card title |
| `source_type` | ✅ | `resume` | Filtering, card styling |
| `section` | ✅ | `Experience — Acme Corp` | Citation card subtitle |
| `text` | ✅ | *chunk content* | Excerpt shown + what LLM reads |
| `source_url` | ❌ | `https://github.com/...` | Clickable card when available |
| `content_hash` | ✅ | `sha256:...` | Idempotent upsert |
| `ingested_at` | ✅ | `2026-08-14T...` | Freshness display |

`section` is what a human reads on the citation card. Make it descriptive. `"Section 3"`
is useless; `"Experience — Acme Corp, Backend Engineer (2023–2025)"` is a citation.

---

## 5. Embedding

**Model:** `BAAI/bge-small-en-v1.5` (384 dims) via `sentence-transformers`. Local, CPU,
free, no rate limit. Alternative: `all-MiniLM-L6-v2` (also 384 dims, smaller/faster).

**Critical:** the vector column dimension must match the model exactly. Changing models
later means re-creating the column and re-embedding everything. Decide now.

For `bge` models specifically, prefix **queries** (not documents) with the model's
recommended instruction prefix — check the model card. Skipping this costs retrieval
quality for free.

---

## 6. Idempotency

Re-running ingestion on unchanged input must not duplicate rows (FR-6.4).

1. Compute `content_hash` from chunk text + source + section.
2. Unique constraint on `content_hash`.
3. Upsert on conflict; update `ingested_at`.
4. After a full run, delete rows whose `source` was processed but whose hash wasn't seen
   — this removes content deleted at the source.

Without step 4, deleting a project from GitHub leaves the bot still citing it. That's a
real correctness bug, not a nicety.

---

## 7. GitHub MCP integration

The official GitHub MCP server is maintained by GitHub and uses proper OAuth/PAT auth —
no scraping.

**What to pull:** repo list (name, description, topics, language, stars, updated date),
README content per repo, optionally recent commit activity for a live-facts tool.

**What to skip:** forks you didn't meaningfully modify, archived experiments, anything
with no README. Curate — a bot that cites `test-repo-3` looks careless.

**Auth:** a fine-grained PAT with read-only public repo scope. Store as
`GITHUB_TOKEN` env var. Never commit it.

**Where MCP sits:** the ingestion job is an MCP *client*. This is the layer where MCP
belongs — offline, no latency pressure, unbounded time budget. See ADR-002 for why it
does not belong on the query path.

---

## 8. Scheduling

**Option A — GitHub Actions (recommended, free).** Workflow on a `schedule` cron, daily.
Runs `ingest.py` with secrets from repo settings. Zero infra, visible run history, and
"my corpus refreshes via CI" is a clean story.

**Option B — Fly.io / Render cron.** If already deployed there.

**Option C — Webhook.** GitHub webhook on push triggers ingestion. Freshest, most
complex. Only if ahead of schedule.

Start with A.

---

## 9. Validation

After every ingestion run, assert and log:

- Total chunk count is non-zero and within an expected range
- No chunk exceeds the token ceiling
- No chunk is under the floor
- Every chunk has non-null `source` and `section`
- Embedding dimensions match the column
- No duplicate `content_hash`

Then **spot check by querying**: run 5 known questions against the fresh store and print
the top result for each. If "what did you do at [company]?" doesn't return that
company's chunk first, fix chunking before touching the voice pipeline. Debugging bad
retrieval through a voice interface is miserable — validate at the data layer.

---

## 10. Corpus checklist

Before Phase 3, you should have:

- [ ] `corpus/resume.pdf`
- [ ] `corpus/context.md` — handwritten, 1,000+ words
- [ ] `corpus/projects/` — 3–6 curated project descriptions
- [ ] `corpus/linkedin/` — from official export (optional)
- [ ] GitHub PAT in `.env`
- [ ] Ingestion produces 40–150 chunks (typical healthy range)
- [ ] All 5 spot-check queries return the right top chunk
