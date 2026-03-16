"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import { createLogger } from "@/lib/logger";
import { getToken, computeMetricsAverages } from "@/lib/livekit";
import type { Subject, TurnMetrics, MetricsAverages, ConnectionState, WhiteboardPayload } from "@/lib/types";
import AvatarDisplay from "@/components/AvatarDisplay";
import AvatarPiP from "@/components/AvatarPiP";
import WhiteboardCanvas from "@/components/WhiteboardCanvas";
import ConnectionStatus from "@/components/ConnectionStatus";
import LatencyOverlay from "@/components/LatencyOverlay";
import SessionControls from "@/components/SessionControls";
import TranscriptSidebar from "@/components/TranscriptSidebar";
import type { TranscriptEntry } from "@/components/TranscriptSidebar";
import SessionInner from "./SessionInner";

const logger = createLogger("SessionPage");

const SUBJECT_LABELS: Record<Subject, string> = {
  biology: "Biology",
  math: "Math",
  earth_science: "Earth Science",
  intro_algebra: "Intro Algebra",
  algebra_ii: "Algebra II",
  chemistry: "Chemistry",
  cell_biology: "Cell Biology",
  world_history: "World History",
  calculus: "Calculus",
  physics: "Physics",
  ap_biology: "AP Biology",
};

const VALID_SUBJECTS = new Set<Subject>(Object.keys(SUBJECT_LABELS) as Subject[]);

function isValidSubject(s: string | null): s is Subject {
  return VALID_SUBJECTS.has(s as Subject);
}

interface TokenState {
  token: string;
  url: string;
}

function SessionContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const rawSubject = searchParams.get("subject");
  const subject: Subject = isValidSubject(rawSubject) ? rawSubject : "biology";

  const rawGrade = searchParams.get("grade");
  const grade = rawGrade && /^([6-9]|1[0-2])$/.test(rawGrade) ? parseInt(rawGrade, 10) : undefined;

  const [tokenState, setTokenState] = useState<TokenState | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [isLoadingToken, setIsLoadingToken] = useState(true);
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [latestMetrics, setLatestMetrics] = useState<TurnMetrics | undefined>(undefined);
  const [metricsHistory, setMetricsHistory] = useState<readonly TurnMetrics[]>([]);
  const [metricsAverages, setMetricsAverages] = useState<MetricsAverages | null>(null);
  const [metricsVisible, setMetricsVisible] = useState(false);
  const [transcriptEntries, setTranscriptEntries] = useState<readonly TranscriptEntry[]>([]);
  const [transcriptVisible, setTranscriptVisible] = useState(true);
  const [agentVolume, setAgentVolume] = useState(0.8);
  const [isConnected, setIsConnected] = useState(false);
  const [whiteboardPayload, setWhiteboardPayload] = useState<WhiteboardPayload | null>(null);
  const [isWhiteboardActive, setIsWhiteboardActive] = useState(false);
  const sendMessageRef = useRef<((text: string) => void) | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchToken() {
      setIsLoadingToken(true);
      setTokenError(null);
      try {
        const result = await getToken(subject, grade);
        if (!cancelled) {
          setTokenState(result);
          logger.info("token_ready", { subject, grade });
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Failed to connect";
          setTokenError(message);
          logger.error("token_fetch_error", { subject, error: message });
        }
      } finally {
        if (!cancelled) {
          setIsLoadingToken(false);
        }
      }
    }

    void fetchToken();
    return () => { cancelled = true; };
  }, [subject, grade]);

  const handleConnectionStateChange = useCallback((state: ConnectionState) => {
    setConnectionState(state);
    setIsConnected(state === "connected");
    logger.info("connection_state_changed", { state });
  }, []);

  const handleMetricsUpdate = useCallback((metrics: TurnMetrics) => {
    setLatestMetrics(metrics);
    setMetricsHistory((prev) => {
      const updated = [...prev, metrics];
      setMetricsAverages(computeMetricsAverages(updated));
      logger.debug("metrics_history_updated", { turn_count: updated.length });
      return updated;
    });
  }, []);

  const handleWhiteboardUpdate = useCallback((payload: WhiteboardPayload) => {
    setWhiteboardPayload(payload);
    setIsWhiteboardActive(true);
  }, []);

  const handleToggleMetrics = useCallback(() => {
    setMetricsVisible((prev) => {
      logger.info("metrics_visibility_toggled", { visible: !prev });
      return !prev;
    });
  }, []);

  const handleTranscriptUpdate = useCallback((entry: TranscriptEntry) => {
    setTranscriptEntries((prev) => {
      const idx = prev.findIndex((e) => e.id === entry.id);
      if (idx >= 0) {
        // Upsert: replace existing entry with updated text (same stream)
        return [...prev.slice(0, idx), entry, ...prev.slice(idx + 1)];
      }
      return [...prev, entry];
    });
  }, []);

  const handleToggleTranscript = useCallback(() => {
    setTranscriptVisible((prev) => {
      logger.info("transcript_visibility_toggled", { visible: !prev });
      return !prev;
    });
  }, []);

  const handleEndSession = useCallback(() => {
    logger.info("session_ended", { subject });
    router.push("/");
  }, [router, subject]);

  const handleStartSession = useCallback(() => {
    if (!tokenState && !isLoadingToken) {
      setIsLoadingToken(true);
      setTokenError(null);
      getToken(subject, grade)
        .then((result) => {
          setTokenState(result);
          setIsLoadingToken(false);
        })
        .catch((err) => {
          const message = err instanceof Error ? err.message : "Failed to connect";
          setTokenError(message);
          setIsLoadingToken(false);
        });
    }
  }, [tokenState, isLoadingToken, subject, grade]);

  const handleSendMessageReady = useCallback((sendFn: (text: string) => void) => {
    sendMessageRef.current = sendFn;
  }, []);

  const handleSendMessage = useCallback((text: string) => {
    // Add to transcript immediately so user sees their message
    const id = `typed-${Date.now()}`;
    setTranscriptEntries((prev) => [
      ...prev,
      { id, role: "user", text, timestamp: Date.now() },
    ]);
    // Send via LiveKit data channel to the agent
    sendMessageRef.current?.(text);
    logger.info("text_message_submitted", { length: text.length });
  }, []);

  if (isLoadingToken) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-950">
        <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-400 text-sm">Connecting to session…</p>
      </main>
    );
  }

  if (tokenError || !tokenState) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gray-950 px-4">
        <div className="bg-red-900/40 border border-red-700 rounded-lg p-6 max-w-md text-center">
          <h2 className="text-red-300 font-semibold text-lg mb-2">Connection Error</h2>
          <p className="text-red-400 text-sm">{tokenError ?? "Unable to retrieve session credentials."}</p>
          <button
            onClick={() => router.push("/")}
            className="mt-4 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 text-sm"
          >
            Return Home
          </button>
        </div>
      </main>
    );
  }

  return (
    <LiveKitRoom
      token={tokenState.token}
      serverUrl={tokenState.url}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={handleEndSession}
    >
      <RoomAudioRenderer volume={agentVolume} />
      <SessionInner
        subject={subject}
        onConnectionStateChange={handleConnectionStateChange}
        onMetricsUpdate={handleMetricsUpdate}
        onTranscriptUpdate={handleTranscriptUpdate}
        onWhiteboardUpdate={handleWhiteboardUpdate}
        onSendMessageReady={handleSendMessageReady}
      />
      <div className="flex min-h-screen bg-gray-950 text-white">
        <main className="flex flex-1 flex-col">
          <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
            <div>
              <h1 className="text-xl font-bold">{SUBJECT_LABELS[subject]} Tutor</h1>
              <p className="text-xs text-gray-400">Real-time AI tutoring session</p>
            </div>
            <ConnectionStatus state={connectionState} />
          </header>
          <div className="flex-1 flex items-center justify-center p-6">
            {isWhiteboardActive ? (
              <div className="w-full max-w-4xl h-full">
                <WhiteboardCanvas payload={whiteboardPayload} />
              </div>
            ) : (
              <div className="w-full max-w-3xl">
                <AvatarDisplay />
              </div>
            )}
          </div>
          <AvatarPiP isActive={isWhiteboardActive} />
          <LatencyOverlay
            metrics={latestMetrics}
            averages={metricsAverages}
            visible={metricsVisible}
          />
          <footer className="flex items-center justify-center px-6 py-5 border-t border-gray-800">
            <SessionControls
              isConnected={isConnected}
              onStart={handleStartSession}
              onEnd={handleEndSession}
              metricsVisible={metricsVisible}
              onToggleMetrics={handleToggleMetrics}
              transcriptVisible={transcriptVisible}
              onToggleTranscript={handleToggleTranscript}
              volume={agentVolume}
              onVolumeChange={setAgentVolume}
            />
          </footer>
        </main>
        <TranscriptSidebar
          entries={transcriptEntries}
          visible={transcriptVisible}
          onSendMessage={handleSendMessage}
          isConnected={isConnected}
        />
      </div>
    </LiveKitRoom>
  );
}

export default function SessionPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-950">
          <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400 text-sm">Loading session…</p>
        </main>
      }
    >
      <SessionContent />
    </Suspense>
  );
}
