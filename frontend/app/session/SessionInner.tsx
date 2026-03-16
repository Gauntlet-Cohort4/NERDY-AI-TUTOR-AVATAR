"use client";

import { useCallback, useEffect, useRef } from "react";
import { useConnectionState, useDataChannel, useRoomContext, useTranscriptions } from "@livekit/components-react";
import { ConnectionState as LKConnectionState } from "livekit-client";
import { mapConnectionState, parseMetricsMessage, parseWhiteboardPayload } from "@/lib/livekit";
import { createLogger } from "@/lib/logger";
import type { TranscriptEntry } from "@/components/TranscriptSidebar";
import type { ConnectionState, TurnMetrics, WhiteboardPayload } from "@/lib/types";

const logger = createLogger("SessionInner");

interface SessionInnerProps {
  subject: string;
  onConnectionStateChange: (state: ConnectionState) => void;
  onMetricsUpdate: (metrics: TurnMetrics) => void;
  onTranscriptUpdate: (entry: TranscriptEntry) => void;
  onWhiteboardUpdate: (payload: WhiteboardPayload) => void;
  onSendMessageReady: (sendFn: (text: string) => void) => void;
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
  onWhiteboardUpdate,
  onSendMessageReady,
}: SessionInnerProps) {
  const lkConnectionState: LKConnectionState = useConnectionState();
  const room = useRoomContext();

  // Sync LiveKit connection state up to the parent.
  useEffect(() => {
    const mapped = mapConnectionState(lkConnectionState);
    logger.debug("lk_connection_state", { raw: lkConnectionState, mapped, subject });
    onConnectionStateChange(mapped);
  }, [lkConnectionState, onConnectionStateChange, subject]);

  // Expose the text send function to parent once room is available.
  useEffect(() => {
    if (!room?.localParticipant) return;

    const sendFn = (text: string) => {
      const payload = new TextEncoder().encode(text);
      room.localParticipant.publishData(payload, { reliable: true, topic: "chat_input" });
      logger.info("text_message_sent", { length: text.length });
    };

    onSendMessageReady(sendFn);
  }, [room, onSendMessageReady]);

  // Subscribe to the agent's data channel for metrics messages.
  const handleMetrics = useCallback(
    (message: { payload: Uint8Array }) => {
      const metrics = parseMetricsMessage(message.payload);
      if (metrics !== null) {
        logger.debug("metrics_received", { turn: metrics.turn });
        onMetricsUpdate(metrics);
      }
    },
    [onMetricsUpdate],
  );
  useDataChannel("metrics", handleMetrics);

  // Subscribe to the agent's data channel for whiteboard payloads.
  const handleWhiteboard = useCallback(
    (message: { payload: Uint8Array | string }) => {
      const payload = parseWhiteboardPayload(message.payload);
      if (payload !== null) {
        logger.debug("whiteboard_received", { type: payload.type });
        onWhiteboardUpdate(payload);
      }
    },
    [onWhiteboardUpdate],
  );
  useDataChannel("whiteboard", handleWhiteboard);

  // Transcript fallback: Beyond Presence can desync the TranscriptSynchronizer,
  // truncating the text stream. The agent publishes the complete response text on
  // the "transcript_complete" data channel. We patch the latest agent bubble if
  // the complete text is longer than what useTranscriptions() delivered.
  const latestAgentBubbleId = useRef<string | null>(null);

  const handleTranscriptComplete = useCallback(
    (message: { payload: Uint8Array }) => {
      try {
        const decoded = new TextDecoder().decode(message.payload);
        const { text } = JSON.parse(decoded) as { text: string };
        const bubbleId = latestAgentBubbleId.current;
        if (bubbleId && text) {
          onTranscriptUpdate({
            id: bubbleId,
            role: "agent",
            text,
            timestamp: Date.now(),
          });
        }
      } catch {
        // Ignore malformed payloads
      }
    },
    [onTranscriptUpdate],
  );
  useDataChannel("transcript_complete", handleTranscriptComplete);

  // Capture live transcriptions (both user STT and agent responses).
  // Agent speech: each response gets its own streamInfo.id — one bubble per reply.
  // User STT: Deepgram sends many small segments, each with a unique stream ID.
  // We consolidate user segments into a single rolling bubble using a stable ref ID
  // that only advances when an agent response arrives (meaning the user finished).
  const transcriptions = useTranscriptions();
  const userUtteranceId = useRef<string>(`user-${Date.now()}`);
  const lastRoleRef = useRef<"user" | "agent">("user");
  // Cache: streamInfo.id → assigned bubble ID (stable across re-renders)
  const assignedIds = useRef<Map<string, string>>(new Map());
  // Cache: streamInfo.id → last emitted text (skip unchanged segments)
  const lastSeenText = useRef<Map<string, string>>(new Map());
  // Accumulator: bubbleId → Map<segmentKey, latest text> for user bubbles
  const bubbleSegments = useRef<Map<string, Map<string, string>>>(new Map());

  useEffect(() => {
    let dirtyBubbles: Set<string> | null = null;

    for (const t of transcriptions) {
      if (!t.text || t.text.trim().length < 2) continue;

      const segmentKey = t.streamInfo.id;
      const trimmedText = t.text.trim();

      // Skip if text hasn't changed since last emit for this segment
      if (lastSeenText.current.get(segmentKey) === trimmedText) continue;
      lastSeenText.current.set(segmentKey, trimmedText);

      const isAgent = t.participantInfo.identity.startsWith("agent");

      // Look up or assign a stable bubble ID for this segment
      let bubbleId = assignedIds.current.get(segmentKey);
      if (!bubbleId) {
        if (isAgent) {
          bubbleId = segmentKey;
          latestAgentBubbleId.current = bubbleId;
          if (lastRoleRef.current === "user") {
            lastRoleRef.current = "agent";
          }
        } else {
          if (lastRoleRef.current === "agent") {
            userUtteranceId.current = `user-${Date.now()}`;
            lastRoleRef.current = "user";
          }
          bubbleId = userUtteranceId.current;
        }
        assignedIds.current.set(segmentKey, bubbleId);
      }

      if (isAgent) {
        // Agent bubbles: one segment per bubble, emit directly
        onTranscriptUpdate({
          id: bubbleId,
          role: "agent",
          text: trimmedText,
          timestamp: Date.now(),
        });
      } else {
        // User bubbles: accumulate segments, emit combined text
        if (!bubbleSegments.current.has(bubbleId)) {
          bubbleSegments.current.set(bubbleId, new Map());
        }
        bubbleSegments.current.get(bubbleId)!.set(segmentKey, trimmedText);
        if (!dirtyBubbles) dirtyBubbles = new Set();
        dirtyBubbles.add(bubbleId);
      }
    }

    // Emit accumulated user bubbles that changed this pass
    if (dirtyBubbles) {
      for (const bubbleId of dirtyBubbles) {
        const segments = bubbleSegments.current.get(bubbleId);
        if (!segments) continue;
        const combined = Array.from(segments.values()).join(" ");
        onTranscriptUpdate({
          id: bubbleId,
          role: "user",
          text: combined,
          timestamp: Date.now(),
        });
      }
    }
  }, [transcriptions, onTranscriptUpdate]);

  // This component renders nothing — it is purely a hook bridge.
  return null;
}
