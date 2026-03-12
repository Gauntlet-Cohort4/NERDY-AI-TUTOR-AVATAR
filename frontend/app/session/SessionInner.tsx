"use client";

import { useEffect } from "react";
import { useConnectionState, useDataChannel, useTranscriptions } from "@livekit/components-react";
import { ConnectionState as LKConnectionState } from "livekit-client";
import { mapConnectionState, parseMetricsMessage } from "@/lib/livekit";
import { createLogger } from "@/lib/logger";
import type { TranscriptEntry } from "@/components/TranscriptSidebar";
import type { ConnectionState, TurnMetrics } from "@/lib/types";

const logger = createLogger("SessionInner");

interface SessionInnerProps {
  subject: string;
  onConnectionStateChange: (state: ConnectionState) => void;
  onMetricsUpdate: (metrics: TurnMetrics) => void;
  onTranscriptUpdate: (entry: TranscriptEntry) => void;
}

/**
 * Must be rendered inside a <LiveKitRoom>.
 * Bridges LiveKit hooks to parent-managed state without exposing hook calls
 * outside the room context.
 */
export default function SessionInner({
  subject,
  onConnectionStateChange,
  onMetricsUpdate,
  onTranscriptUpdate,
}: SessionInnerProps) {
  const lkConnectionState: LKConnectionState = useConnectionState();

  // Sync LiveKit connection state up to the parent.
  useEffect(() => {
    const mapped = mapConnectionState(lkConnectionState);
    logger.debug("lk_connection_state", { raw: lkConnectionState, mapped, subject });
    onConnectionStateChange(mapped);
  }, [lkConnectionState, onConnectionStateChange, subject]);

  // Subscribe to the agent's data channel for metrics messages.
  useDataChannel("metrics", (message) => {
    const metrics = parseMetricsMessage(message.payload);
    if (metrics !== null) {
      logger.debug("metrics_received", { turn: metrics.turn });
      onMetricsUpdate(metrics);
    }
  });

  // Capture live transcriptions (both user STT and agent responses).
  // Each stream has a stable ID — we upsert the same entry as text grows,
  // so the sidebar shows one card per utterance that updates in real time.
  const transcriptions = useTranscriptions();

  useEffect(() => {
    for (const t of transcriptions) {
      if (!t.text || t.text.trim().length < 2) continue;

      const streamId = t.streamInfo?.id ?? `${t.participantInfo.identity}-${Date.now()}`;
      const isAgent = t.participantInfo.identity.startsWith("agent");

      const entry: TranscriptEntry = {
        id: streamId,
        role: isAgent ? "agent" : "user",
        text: t.text.trim(),
        timestamp: Date.now(),
      };

      onTranscriptUpdate(entry);
    }
  }, [transcriptions, onTranscriptUpdate]);

  // This component renders nothing — it is purely a hook bridge.
  return null;
}
