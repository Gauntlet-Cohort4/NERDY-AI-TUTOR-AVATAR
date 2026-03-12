"use client";

import { useEffect, useState } from "react";
import { useRemoteParticipants } from "@livekit/components-react";
import { Track } from "livekit-client";
import { createLogger } from "@/lib/logger";

const logger = createLogger("AvatarDisplay");

/**
 * Renders the first remote participant's camera video track.
 * Shows a swirling particle effect while loading, then crossfades to the avatar.
 */
export default function AvatarDisplay() {
  const remoteParticipants = useRemoteParticipants();
  const [revealed, setRevealed] = useState(false);

  const agentParticipant = remoteParticipants.find((p) => {
    const pub = p.getTrackPublication(Track.Source.Camera);
    return pub !== undefined && !pub.isMuted;
  });

  const trackPublication = agentParticipant?.getTrackPublication(Track.Source.Camera);
  const track = trackPublication?.track;

  // When the track arrives, trigger the reveal transition
  useEffect(() => {
    if (track && !revealed) {
      const timer = setTimeout(() => setRevealed(true), 300);
      return () => clearTimeout(timer);
    }
  }, [track, revealed]);

  return (
    <div className="relative aspect-video w-full bg-gray-900 rounded-xl overflow-hidden shadow-2xl">
      {/* Video layer — always mounted once track exists, fades in */}
      {track && (
        <div
          className={`absolute inset-0 z-10 transition-opacity duration-1000 ${
            revealed ? "opacity-100" : "opacity-0"
          }`}
        >
          <VideoRenderer track={track} participantIdentity={agentParticipant?.identity ?? ""} />
        </div>
      )}

      {/* Loading layer — swirling effect, fades out when avatar reveals */}
      <div
        className={`absolute inset-0 z-20 transition-opacity duration-1000 pointer-events-none ${
          revealed ? "opacity-0" : "opacity-100"
        }`}
      >
        <LoadingEffect />
      </div>
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

function LoadingEffect() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-gray-950">
      {/* Radial gradient backdrop */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(59,130,246,0.08)_0%,_transparent_70%)]" />

      {/* Orbiting particles */}
      <div className="relative w-48 h-48">
        {/* Ring 1 — slow outer orbit */}
        <div className="absolute inset-0 animate-[spin_8s_linear_infinite]">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-blue-400/60 blur-[2px]" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-purple-400/50 blur-[2px]" />
        </div>

        {/* Ring 2 — medium orbit, counter-direction */}
        <div className="absolute inset-6 animate-[spin_5s_linear_infinite_reverse]">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-cyan-400/60 blur-[1px]" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-blue-300/50 blur-[1px]" />
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-indigo-400/40 blur-[1px]" />
        </div>

        {/* Ring 3 — fast inner orbit */}
        <div className="absolute inset-12 animate-[spin_3s_linear_infinite]">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-blue-300/70 blur-[1px]" />
          <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-1 rounded-full bg-purple-300/60 blur-[1px]" />
        </div>

        {/* Center glow */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-16 h-16 rounded-full bg-blue-500/10 animate-pulse" />
          <div className="absolute w-8 h-8 rounded-full bg-blue-400/20 animate-[pulse_2s_ease-in-out_infinite]" />
        </div>
      </div>

      {/* Status text */}
      <p className="absolute bottom-8 text-gray-400 text-sm animate-pulse tracking-wide">
        Preparing your tutor&hellip;
      </p>
    </div>
  );
}
