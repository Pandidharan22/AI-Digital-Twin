# Corpus

Source documents for ingestion: `AI Engineer Resume.pdf`, `context.md` (handwritten,
see `docs/DATA_INGESTION.md` Sec2), and optionally `projects/`/`linkedin/` (official
data export only -- see ADR-003).

**Privacy decision (resolved 2026-08-18):** these files carry personal contact info
(phone, email), so `corpus/*` is gitignored except this README -- source documents are
ingested into Supabase and the deployed bot can cite them, but the raw files never land
in public git history. Anyone cloning the repo needs to supply their own corpus files
locally before running ingestion.
