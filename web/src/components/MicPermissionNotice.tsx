import { useEffect, useState } from "react";
import { useRoomContext } from "@livekit/components-react";
import { RoomEvent } from "livekit-client";

// DEPLOYMENT.md's pre-submission checklist: "Mic-denied path shows a helpful
// message." Mic access is opt-in via the ControlBar toggle (not requested on
// connect -- see docs/DEV_JOURNAL.md's LiveKitRoom `audio` prop fix), so this
// only ever fires from an explicit, visitor-initiated request, and only needs
// to explain what to do next when the browser denies it.
export function MicPermissionNotice() {
  const room = useRoomContext();
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    const onError = (_error: Error, kind?: MediaDeviceKind) => {
      if (!kind || kind === "audioinput") setDenied(true);
    };
    room.on(RoomEvent.MediaDevicesError, onError);
    return () => {
      room.off(RoomEvent.MediaDevicesError, onError);
    };
  }, [room]);

  if (!denied) {
    return (
      <p className="mic-explainer">
        Click the microphone button below and allow mic access to talk. Nothing is
        recorded until you do.
      </p>
    );
  }

  return (
    <p className="mic-explainer mic-explainer-error">
      Microphone access was blocked. Check your browser's site permissions (usually
      the lock/camera icon in the address bar) and allow the microphone, then click
      the button again.
    </p>
  );
}
