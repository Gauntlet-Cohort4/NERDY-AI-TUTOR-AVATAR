"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import { createLogger } from "@/lib/logger";
import { getToken, computeMetricsAverages } from "@/lib/livekit";
import type { Subject, TurnMetrics, MetricsAverages, ConnectionState } from "@/lib/types";
import AvatarDisplay from "@/components/AvatarDisplay";
import ConnectionStatus from "@/components/ConnectionStatus";
import LatencyOverlay from "@/components/LatencyOverlay";
import SessionControls from "@/components/SessionControls";
import SessionInner from "./SessionInner";

const logger = createLogger("SessionPage");

const VALID_SUBJECTS = new Set<Subject>(["biology", "math", "physics"]);

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

  const [tokenState, setTokenState] = useState<TokenState | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [isLoadingToken, setIsLoadingToken] = useState(true);
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [latestMetrics, setLatestMetrics] = useState<TurnMetrics | undefined>(undefined);
  const [metricsHistory, setMetricsHistory] = useState<readonly TurnMetrics[]>([]);
  const [metricsAverages, setMetricsAverages] = useState<MetricsAverages | null>(null);
  const [metricsVisible, setMetricsVisible] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchToken() {
      setIsLoadingToken(true);
      setTokenError(null);
      try {
        const result = await getToken(subject);
        if (!cancelled) {
          setTokenState(result);
          logger.info("token_ready", { subject });
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
  }, [subject]);

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

  const handleToggleMetrics = useCallback(() => {
    setMetricsVisible((prev) => {
      logger.info("metrics_visibility_toggled", { visible: !prev });
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
      getToken(subject)
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
  }, [tokenState, isLoadingToken, subject]);

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
      <RoomAudioRenderer />
      <SessionInner
        subject={subject}
        onConnectionStateChange={handleConnectionStateChange}
        onMetricsUpdate={handleMetricsUpdate}
      />
      <main className="flex min-h-screen flex-col bg-gray-950 text-white">
        <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h1 className="text-xl font-bold capitalize">{subject} Tutor</h1>
            <p className="text-xs text-gray-400">Real-time AI tutoring session</p>
          </div>
          <ConnectionStatus state={connectionState} />
        </header>
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="relative w-full max-w-3xl">
            <AvatarDisplay />
            <LatencyOverlay
              metrics={latestMetrics}
              averages={metricsAverages}
              visible={metricsVisible}
            />
          </div>
        </div>
        <footer className="flex items-center justify-center px-6 py-5 border-t border-gray-800">
          <SessionControls
            isConnected={isConnected}
            onStart={handleStartSession}
            onEnd={handleEndSession}
            metricsVisible={metricsVisible}
            onToggleMetrics={handleToggleMetrics}
          />
        </footer>
      </main>
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
