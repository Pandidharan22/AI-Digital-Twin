import { useCallback, useState } from "react";
import { useDataChannel } from "@livekit/components-react";
import type { CitationPayload } from "../types/citations";

const TOPIC = "citations";
const decoder = new TextDecoder();

/**
 * Listens on the "citations" data-channel topic and renders a compact source
 * reference below each turn -- just what was retrieved (source + section,
 * linked when a URL exists), never the raw chunk text. The excerpt field
 * still travels over the wire (useful for debugging) but is deliberately not
 * rendered; a citation here means "here's the receipt," not "here's the
 * paragraph it was pulled from."
 *
 * FR-4.6 ("no stale cards implying grounding that doesn't exist") is
 * satisfied by never merging or accumulating sources across turns -- each
 * turn's entry renders exactly what that turn's own payload said, including
 * an empty sources[] on no_match.
 */
export function CitationsPanel() {
  const [turns, setTurns] = useState<CitationPayload[]>([]);

  const onMessage = useCallback((msg: { payload: Uint8Array }) => {
    let payload: CitationPayload;
    try {
      payload = JSON.parse(decoder.decode(msg.payload));
    } catch (err) {
      console.error("Malformed citations payload", err);
      return;
    }
    setTurns((prev) => [...prev, payload]);
  }, []);

  useDataChannel(TOPIC, onMessage);

  if (turns.length === 0) return null;

  return (
    <div className="citations-feed">
      {turns.map((turn) => (
        <div key={turn.turn_id} className="citation-turn">
          {turn.status === "no_match" || turn.sources.length === 0 ? (
            <span className="citation-no-source">No documented source</span>
          ) : (
            <div className="citation-chips">
              {turn.sources.map((source) =>
                source.url ? (
                  <a
                    key={source.id}
                    className="citation-chip"
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {source.section}
                    <span className="citation-chip-source">{source.source}</span>
                  </a>
                ) : (
                  <span key={source.id} className="citation-chip">
                    {source.section}
                    <span className="citation-chip-source">{source.source}</span>
                  </span>
                ),
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
