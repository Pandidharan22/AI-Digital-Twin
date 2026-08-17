"""Centralized configuration.

Loads all runtime settings from environment variables: provider model IDs
(GEMINI_MODEL, EMBEDDING_MODEL), retrieval tuning (RETRIEVAL_THRESHOLD,
RETRIEVAL_TOP_K), and identity (OWNER_NAME). No secrets, thresholds, or model
IDs are hardcoded elsewhere in the codebase.

Covers: NFR-6.1, NFR-6.2.
"""
