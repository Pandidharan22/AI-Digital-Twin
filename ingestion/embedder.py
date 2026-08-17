"""Local embedding.

Wraps sentence-transformers BAAI/bge-small-en-v1.5 (384 dims), CPU inference,
batched. Applies the model's recommended query-instruction prefix at query time
(not at document-embedding time). No hosted embedding API in the loop.

Covers: ADR-006. See DATA_INGESTION.md Sec5.
"""
