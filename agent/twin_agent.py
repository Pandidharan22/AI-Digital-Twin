"""TwinAgent: the Agent subclass carrying the system prompt and the search_my_background
function tool.

Owns per-turn orchestration: deciding when a factual claim requires retrieval,
enforcing the grounding contract (CITATION_SPEC.md Sec5), and refusing gracefully
on no_match.

Covers: FR-3.1, FR-3.4-3.7.
"""
