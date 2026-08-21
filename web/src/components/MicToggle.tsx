import { useLocalParticipant } from "@livekit/components-react";

// Replaces @livekit/components-react's ControlBar prefab, which ships with
// its own default sizing/spacing from @livekit/components-styles far bigger
// than this single-purpose page needs -- a whole toolbar for one button.
// setMicrophoneEnabled(true) is what actually triggers the browser's mic
// permission prompt; MicPermissionNotice listens for the room-level
// mediaDevicesError this throws into on denial.
export function MicToggle() {
  const { localParticipant, isMicrophoneEnabled } = useLocalParticipant();

  return (
    <button
      type="button"
      className={`mic-toggle${isMicrophoneEnabled ? " mic-toggle-on" : ""}`}
      onClick={() => localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled)}
    >
      <span className="mic-toggle-dot" aria-hidden="true" />
      {isMicrophoneEnabled ? "Mic on" : "Tap to talk"}
    </button>
  );
}
