"""Centralized configuration.

Loads all runtime settings from environment variables: provider model IDs
(GEMINI_MODEL, EMBEDDING_MODEL), retrieval tuning (RETRIEVAL_THRESHOLD,
RETRIEVAL_TOP_K), and identity (OWNER_NAME). No secrets, thresholds, or model
IDs are hardcoded elsewhere in the codebase.

Covers: NFR-6.1, NFR-6.2.
"""

import os

from dotenv import load_dotenv

# uv run does not auto-load .env (verified by testing, not assumed) -- load it
# explicitly here so this is the one place env loading happens, regardless of
# how the worker is invoked.
load_dotenv()

# livekit-plugins-google's LLM reads GOOGLE_API_KEY by default, but this
# project's .env (per DEPLOYMENT.md) uses GEMINI_API_KEY. Re-exposed here so
# agent/main.py can pass it explicitly rather than duplicating the secret
# under a second env var name. See docs/SDK_NOTES.md Sec5.
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# "gemini-2.5-flash" and "gemini-2.5-flash-lite" (the plugin's own compiled-in
# default and this project's original Phase 1 pinned choice, respectively)
# both return a live HTTP 404 "no longer available to new users" as of this
# verification -- confirmed by direct generateContent calls, not assumed.
# "gemini-flash-latest", the rolling alias this project switched to in Phase 1
# to dodge exactly that kind of retirement, currently resolves to
# "gemini-3.7-flash" -- a full Flash model whose free-tier limit is only 5
# RPM, confirmed live by a real 429 during Phase 3 voice testing
# (docs/DEV_JOURNAL.md, 2026-08-20).
#
# "gemini-3.5-flash-lite" replaces it here, and is pinned rather than another
# rolling alias -- deliberately: the whole point of "gemini-flash-latest" was
# to avoid depending on a specific model ID, and that's exactly what silently
# changed the RPM budget underfoot when Google moved the alias's target from
# a 10 RPM model to a 5 RPM one with no warning. A pinned ID can't drift; it
# can only 404 outright when retired, which is a loud, obvious failure this
# project already knows how to detect and fix (see the 2.5-generation
# failures above), not a silent budget cut. Verified live (2026-08-21):
# survives 15 rapid successive calls with zero 429s (>=15 RPM, 3x the
# full-Flash figure), and correctly calls/skips search_my_background against
# this project's actual system prompt and tool across three real test
# prompts run through the actual google.LLM plugin -- a greeting (no tool
# call), a factual question (tool called), and the highest-value adversarial
# case, "you worked at Google, right?" (tool called, not agreed with).
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Supabase -- retrieval.py talks to match_chunks() through the supabase-py RPC
# client (same client ingestion/validate.py uses), not a direct psycopg
# connection. No DDL happens at query time, so the service key + REST client
# is sufficient; DATABASE_URL (direct Postgres) stays ingestion-only.
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# Retrieval tuning -- ADR-004's anti-hallucination gate. 0.5 empirically set in
# Phase 2 against this corpus's real out-of-scope similarity scores (see
# docs/ARCHITECTURE.md ADR-004 Outcome); still interim pending Phase 3 tuning
# against the full docs/TEST_PLAN.md question set.
RETRIEVAL_THRESHOLD = float(os.environ.get("RETRIEVAL_THRESHOLD", 0.5))
RETRIEVAL_TOP_K = int(os.environ.get("RETRIEVAL_TOP_K", 4))

# Identity -- substituted into the system prompt (CITATION_SPEC.md Sec5).
OWNER_NAME = os.environ["OWNER_NAME"]
