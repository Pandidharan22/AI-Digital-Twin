import { useEffect, useState } from "react";
import { LiveKitRoom, RoomAudioRenderer, ControlBar } from "@livekit/components-react";
import "@livekit/components-styles";
import { CitationsPanel } from "./components/CitationsPanel";
import { AgentStatus } from "./components/AgentStatus";
import { SuggestedQuestions } from "./components/SuggestedQuestions";
import { MicPermissionNotice } from "./components/MicPermissionNotice";
import "./App.css";

interface TokenResponse {
  token: string;
  url: string;
  room: string;
}

const TOKEN_SERVICE_URL =
  import.meta.env.VITE_TOKEN_SERVICE_URL ?? "http://localhost:8000";

function App() {
  const [connection, setConnection] = useState<TokenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${TOKEN_SERVICE_URL}/token`, { method: "POST" })
      .then((res) => {
        if (!res.ok) throw new Error(`Token request failed: ${res.status}`);
        return res.json() as Promise<TokenResponse>;
      })
      .then(setConnection)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) {
    return (
      <div className="status-message status-message-error">
        <p>Couldn't connect: {error}</p>
        <p>Try reloading the page. If it keeps failing, the service may be waking up
          from idle — wait a few seconds and try again.</p>
      </div>
    );
  }

  if (!connection) {
    return <div className="status-message">Connecting…</div>;
  }

  return (
    <LiveKitRoom
      serverUrl={connection.url}
      token={connection.token}
      onError={(err) => setError(err.message)}
      onDisconnected={() => setConnection(null)}
    >
      <div className="app-layout">
        <div className="conversation-panel">
          <h1>Voice Twin</h1>
          <p>Ask about Pandidharan's background, projects, or experience.</p>
          <AgentStatus />
          <MicPermissionNotice />
          <ControlBar
            controls={{
              microphone: true,
              camera: false,
              chat: false,
              screenShare: false,
              leave: false,
              settings: false,
            }}
          />
          <SuggestedQuestions />
        </div>
        <CitationsPanel />
      </div>
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

export default App;
