"""Ingestion orchestrator.

Ties loaders -> chunker -> embedder -> Supabase upsert into one run. Idempotent:
re-running on unchanged input must not duplicate rows, and rows whose source was
processed but whose content_hash wasn't seen this run get deleted (removes content
that no longer exists at the source).

Covers: FR-6.1, FR-6.4. See DATA_INGESTION.md Sec6.
"""
