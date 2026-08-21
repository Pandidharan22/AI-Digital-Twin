import { useEffect, useMemo, useRef } from "react";
import { useLocalParticipant, useTranscriptions } from "@livekit/components-react";

// FR-5.1: a running transcript of both visitor and agent turns, in the same
// style as LiveKit's own Agent Console/Playground. `useTranscriptions()` is
// the framework's own hook -- AgentSession publishes both the visitor's STT
// output and the agent's TTS-aligned text as text-stream segments
// automatically (topic "lk.transcription"), keyed by a stable segment id that
// updates in place as a segment grows from partial to final. No agent-side
// code was needed for this: it's the same mechanism the Console's own
// transcript view uses.
export function TranscriptPanel() {
  const transcriptions = useTranscriptions();
  const { localParticipant } = useLocalParticipant();
  const bottomRef = useRef<HTMLDivElement>(null);

  const lines = useMemo(
    () => [...transcriptions].sort((a, b) => a.streamInfo.timestamp - b.streamInfo.timestamp),
    [transcriptions],
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [lines]);

  return (
    <div className="transcript-panel">
      <h2>Transcript</h2>
      {lines.length === 0 && <p className="transcript-empty">Nothing said yet.</p>}
      <div className="transcript-lines">
        {lines.map((line) => {
          const isVisitor = line.participantInfo.identity === localParticipant?.identity;
          return (
            <p
              key={line.streamInfo.id}
              className={
                "transcript-line " +
                (isVisitor ? "transcript-line-visitor" : "transcript-line-agent")
              }
            >
              <span className="transcript-speaker">{isVisitor ? "You" : "Twin"}</span>
              {line.text}
            </p>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
