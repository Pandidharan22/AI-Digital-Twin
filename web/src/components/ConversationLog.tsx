import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDataChannel, useLocalParticipant, useTranscriptions } from "@livekit/components-react";
import type { CitationPayload } from "../types/citations";

const TOPIC = "citations";
const decoder = new TextDecoder();

// Maps agent/citations.py's `source_type` (resume | context | github_repo,
// per ingestion/loaders/*.py) to a plain-language document label, and cleans
// up the display text for each -- section headings for GitHub-sourced chunks
// carry a redundant "<repo> — " prefix from ingestion/loaders/github_loader.py's
// _split_readme, since only README.md is ever ingested per repo (curated to
// 6 repos, see docs/DATA_INGESTION.md Sec7).
function describeSource(source: { source: string; source_type: string; section: string }) {
  if (source.source_type === "resume") {
    return { label: source.section, doc: "Resume" };
  }
  if (source.source_type === "context") {
    return { label: source.section, doc: "Notes (context.md)" };
  }
  if (source.source_type === "github_repo") {
    const prefix = `${source.source} — `;
    const label = source.section.startsWith(prefix)
      ? source.section.slice(prefix.length)
      : source.section;
    return { label, doc: `${source.source} — README.md` };
  }
  return { label: source.section, doc: source.source };
}

function Citation({ turn }: { turn: CitationPayload }) {
  if (turn.status === "no_match" || turn.sources.length === 0) {
    return <span className="citation-no-source">No documented source</span>;
  }
  return (
    <div className="citation-chips">
      {turn.sources.map((source) => {
        const { label, doc } = describeSource(source);
        return source.url ? (
          <a
            key={source.id}
            className="citation-chip"
            href={source.url}
            target="_blank"
            rel="noreferrer"
          >
            {label}
            <span className="citation-chip-source">{doc}</span>
          </a>
        ) : (
          <span key={source.id} className="citation-chip">
            {label}
            <span className="citation-chip-source">{doc}</span>
          </span>
        );
      })}
    </div>
  );
}

/**
 * Transcript (FR-5.1) and citations (FR-4.1/4.2), merged into one feed so
 * each agent message shows its own evidence directly underneath it, instead
 * of two separately-scrolling lists (a real UX gap found in the 2026-08-23
 * mobile test: citations from every turn piled up in one block at the
 * bottom, disconnected from which message they actually backed).
 *
 * The two data sources have no shared id to join on -- transcript segments
 * come from `lk.transcription` (LiveKit's own STT/TTS-alignment pipeline);
 * citations come from agent/citations.py's own "citations" topic. Both carry
 * real wall-clock epoch-ms timestamps though (verified live, not assumed:
 * streamInfo.timestamp and Date.now() are the same magnitude/epoch), and
 * ADR-005 guarantees a citation is always published *before* the agent's
 * reply starts generating -- so each agent transcript line claims the
 * earliest not-yet-claimed citation whose timestamp precedes it. A reply
 * the model chose not to search for at all (greetings, or an obviously
 * off-topic question it recognizes without searching) correctly gets no
 * citation, since none was ever published for that turn -- not treated as
 * a "no source" case, since the tool was never called.
 */
export function ConversationLog() {
  const transcriptions = useTranscriptions();
  const { localParticipant } = useLocalParticipant();
  const [citations, setCitations] = useState<CitationPayload[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const onMessage = useCallback((msg: { payload: Uint8Array }) => {
    let payload: CitationPayload;
    try {
      payload = JSON.parse(decoder.decode(msg.payload));
    } catch (err) {
      console.error("Malformed citations payload", err);
      return;
    }
    setCitations((prev) => [...prev, payload]);
  }, []);

  useDataChannel(TOPIC, onMessage);

  const lines = useMemo(
    () => [...transcriptions].sort((a, b) => a.streamInfo.timestamp - b.streamInfo.timestamp),
    [transcriptions],
  );

  const entries = useMemo(() => {
    const sortedCitations = [...citations].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );
    let nextCitation = 0;

    return lines.map((line) => {
      const isVisitor = line.participantInfo.identity === localParticipant?.identity;
      let citation: CitationPayload | undefined;

      if (!isVisitor) {
        while (
          nextCitation < sortedCitations.length &&
          new Date(sortedCitations[nextCitation].timestamp).getTime() <= line.streamInfo.timestamp
        ) {
          citation = sortedCitations[nextCitation];
          nextCitation += 1;
        }
      }

      return { line, isVisitor, citation };
    });
  }, [lines, citations, localParticipant?.identity]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries]);

  if (entries.length === 0) {
    return <p className="transcript-empty">Nothing said yet.</p>;
  }

  return (
    <div className="transcript-lines">
      {entries.map(({ line, isVisitor, citation }) => (
        <div
          key={line.streamInfo.id}
          className={"transcript-turn " + (isVisitor ? "transcript-turn-visitor" : "transcript-turn-agent")}
        >
          <p className="transcript-line">
            <span className="transcript-speaker">{isVisitor ? "You" : "Twin"}</span>
            {line.text}
          </p>
          {citation && <Citation turn={citation} />}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
