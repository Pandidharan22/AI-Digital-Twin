"""Retrieval and grounding gate.

Embeds the incoming query with the same local model used at ingestion time, runs
pgvector cosine-similarity search via Supabase's match_chunks function, and applies
RETRIEVAL_THRESHOLD to decide match vs no_match. Returns the exact contract shape
defined in CITATION_SPEC.md Sec3, including the no_match instruction field.

Covers: FR-3.2, FR-3.3. Load-bearing anti-hallucination layer (ADR-004, L1 in
CITATION_SPEC.md Sec2).
"""
