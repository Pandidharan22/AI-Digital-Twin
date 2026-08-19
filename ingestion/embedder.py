"""Local embedding.

Wraps sentence-transformers BAAI/bge-small-en-v1.5 (384 dims), CPU inference,
batched. No hosted embedding API in the loop -- see ADR-006.

The model card (huggingface.co/BAAI/bge-small-en-v1.5, verified directly rather
than assumed from memory) recommends prefixing *queries only* -- never stored
documents -- with a fixed instruction string for retrieval tasks: "Represent
this sentence for searching relevant passages:". v1.5 improved retrieval
without it, so it's a marginal gain, not a correctness requirement, but it's
free and documented, so applied here at query time only.

Covers: ADR-006. See DATA_INGESTION.md Sec5.
"""

from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_documents(texts: List[str]) -> List[List[float]]:
    """Batch-embed already-prefixed chunk embed_text for storage. No query
    instruction -- the model card is explicit that only queries get it."""
    embeddings = _model().encode(texts, normalize_embeddings=True, batch_size=32)
    return embeddings.tolist()


def embed_query(text: str) -> List[float]:
    prefixed = f"{QUERY_INSTRUCTION}{text}"
    embedding = _model().encode(prefixed, normalize_embeddings=True)
    return embedding.tolist()
