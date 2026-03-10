"use client";

import { useRemoteParticipants } from "@livekit/components-react";
import { Track } from "livekit-client";
import { createLogger } from "@/lib/logger";

const logger = createLogger("AvatarDisplay");

/**
 * Renders the first remote participant's camera video track.
 * Falls back to a placeholder when no track is available.
 */
export default function AvatarDisplay() {
  const remoteParticipants = useRemoteParticipants();

  // Pick the first remote participant that has a camera track (the AI agent).
  const agentParticipant = remoteParticipants.find((p) => {
    const pub = p.getTrackPublication(Track.Source.Camera);
    return pub !== undefined && !pub.isMuted;
  });

  const trackPublication = agentParticipant?.getTrackPublication(Track.Source.Camera);
  const track = trackPublication?.track;

  return (
    <div className="relative aspect-video w-full bg-gray-900 rounded-xl overflow-hidden shadow-2xl">
      {track ? (
        <VideoRenderer track={track} participantIdentity={agentParticipant?.identity ?? ""} />
      ) : (
        <AvatarPlaceholder />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface VideoRendererProps {
  track: { attach: (element: HTMLVideoElement) => void; detach: (element: HTMLVideoElement) => void };
  participantIdentity: string;
}

function VideoRenderer({ track, participantIdentity }: VideoRendererProps) {
  const ref = (el: HTMLVideoElement | null) => {
    if (el) {
      logger.debug("attaching_video_track", { participantIdentity });
      track.attach(el);
    }
  };

  return (
    <video
      ref={ref}
      autoPlay
      playsInline
      muted={false}
      className="w-full h-full object-cover"
      aria-label="AI tutor avatar video"
    />
  );
}

function AvatarPlaceholder() {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 select-none">
      {/* Generic avatar silhouette */}
      <div className="w-24 h-24 rounded-full bg-gray-700 flex items-center justify-center">
        <svg
          className="w-14 h-14 text-gray-500"
          fill="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z" />
        </svg>
      </div>
      <p className="text-gray-500 text-sm">Waiting for avatar…</p>
    </div>
  );
}
