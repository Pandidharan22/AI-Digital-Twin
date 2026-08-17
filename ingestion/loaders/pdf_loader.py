"""PDF loader.

Extracts resume/CV text while preserving section structure (one role, one
education entry, one skills block) so the chunker can split on real boundaries
instead of raw character offsets.

See DATA_INGESTION.md Sec1, Sec3.
"""
