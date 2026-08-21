import { useVoiceAssistant } from "@livekit/components-react";

// FR-5.2: the UI SHALL display agent state at every point in the lifecycle --
// never a silent gap between "connected" and "the bot is actually doing
// something," which is exactly what reads as broken during a cold start
// (docs/DEPLOYMENT.md Sec4's "waking up the agent" guidance).
const LABELS: Record<string, string> = {
  disconnected: "Disconnected",
  connecting: "Connecting…",
  "pre-connect-buffering": "Connecting…",
  failed: "Connection failed",
  initializing: "Waking up the agent — this can take a few seconds…",
  idle: "Ready — say something",
  listening: "Listening…",
  thinking: "Thinking…",
  speaking: "Speaking…",
};

export function AgentStatus() {
  const { state } = useVoiceAssistant();
  const label = LABELS[state] ?? state;
  const isError = state === "failed" || state === "disconnected";

  return (
    <div className={`agent-status${isError ? " agent-status-error" : ""}`}>
      <span className={`agent-status-dot agent-status-dot-${state}`} />
      {label}
    </div>
  );
}
