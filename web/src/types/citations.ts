// Wire schema for the "citations" data-channel topic, per
// docs/CITATION_SPEC.md Sec4. Published by agent/citations.py before the LLM
// generates a reply (ADR-005) -- this is a record of what the retrieval
// layer actually returned, never text the LLM authored.

export interface CitationSource {
  id: string;
  source: string;
  source_type: string;
  section: string;
  excerpt: string;
  score: number;
  url: string | null;
}

export interface CitationPayload {
  type: "citations";
  turn_id: string;
  query: string;
  status: "match" | "no_match";
  timestamp: string;
  sources: CitationSource[];
}
