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

# "gemini-2.5-flash" (the plugin's own compiled-in default, and DEPLOYMENT.md's
# original documented default) returns a live HTTP 404 "no longer available to
# new users" as of this verification -- confirmed by a direct generateContent
# call, not assumed. "gemini-flash-latest" is a rolling alias Google maintains
# to whatever the current recommended flash model is (verified working,
# resolved to "gemini-3.7-flash" at time of writing) -- using the alias avoids
# repeating this exact breakage the next time a pinned version is retired.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

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
