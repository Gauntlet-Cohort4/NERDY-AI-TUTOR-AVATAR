"use client";

import { useEffect } from "react";
import { useConnectionState, useDataChannel } from "@livekit/components-react";
import { ConnectionState as LKConnectionState } from "livekit-client";
import { mapConnectionState, parseMetricsMessage } from "@/lib/livekit";
import { createLogger } from "@/lib/logger";
import type { ConnectionState, TurnMetrics } from "@/lib/types";

const logger = createLogger("SessionInner");

interface SessionInnerProps {
  subject: string;
  onConnectionStateChange: (state: ConnectionState) => void;
  onMetricsUpdate: (metrics: TurnMetrics) => void;
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
}: SessionInnerProps) {
  const lkConnectionState: LKConnectionState = useConnectionState();

  // Sync LiveKit connection state up to the parent.
  useEffect(() => {
    const mapped = mapConnectionState(lkConnectionState);
    logger.debug("lk_connection_state", { raw: lkConnectionState, mapped, subject });
    onConnectionStateChange(mapped);
  }, [lkConnectionState, onConnectionStateChange, subject]);

  // Subscribe to the agent's data channel for metrics messages.
  useDataChannel(undefined, (message) => {
    const metrics = parseMetricsMessage(message.payload);
    if (metrics !== null) {
      logger.debug("metrics_received", { turn: metrics.turn });
      onMetricsUpdate(metrics);
    }
  });

  // This component renders nothing — it is purely a hook bridge.
  return null;
}
