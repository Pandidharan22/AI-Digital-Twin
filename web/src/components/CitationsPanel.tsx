import { useCallback, useState } from "react";
import { useDataChannel } from "@livekit/components-react";
import type { CitationPayload } from "../types/citations";

const TOPIC = "citations";
const decoder = new TextDecoder();

/**
 * Listens on the "citations" data-channel topic and renders source cards
 * keyed by turn_id, newest first.
 *
 * FR-4.6 ("no stale cards implying grounding that doesn't exist") is
 * satisfied by never merging or accumulating sources across turns -- each
 * turn's entry renders exactly what that turn's own payload said, including
 * an empty sources[] on no_match. A no_match turn never inherits or hides
 * behind a prior turn's cards; it gets its own explicit "no source" entry.
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
    setTurns((prev) => [payload, ...prev]);
  }, []);

  useDataChannel(TOPIC, onMessage);

  return (
    <aside className="citations-panel">
      <h2>Sources</h2>
      {turns.length === 0 && (
        <p className="citations-empty">Ask a question to see sources here.</p>
      )}
      {turns.map((turn) => (
        <div key={turn.turn_id} className="citation-turn">
          <p className="citation-query">&ldquo;{turn.query}&rdquo;</p>
          {turn.status === "no_match" || turn.sources.length === 0 ? (
            <p className="citation-no-source">
              No documented source for this question.
            </p>
          ) : (
            <ul className="citation-cards">
              {turn.sources.map((source) => (
                <li key={source.id} className="citation-card">
                  <div className="citation-card-header">
                    <span className="citation-source">{source.source}</span>
                    <span className="citation-score">
                      {source.score.toFixed(2)}
                    </span>
                  </div>
                  <div className="citation-section">{source.section}</div>
                  <p className="citation-excerpt">{source.excerpt}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </aside>
  );
}
