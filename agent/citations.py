"""Citation publishing.

Builds the citation payload exactly per CITATION_SPEC.md Sec4 and publishes it to the
LiveKit data channel (topic "citations"). Fires immediately after retrieval and
BEFORE the LLM generates its reply, per ADR-005, so source cards render before
speech begins. The citation is a record of what was actually retrieved -- never
text the LLM is allowed to author.

Covers: FR-4.1, FR-4.2, FR-4.6.
"""
