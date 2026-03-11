import type { MetricsAverages, TurnMetrics } from "@/lib/types";

interface LatencyOverlayProps {
  metrics?: TurnMetrics;
  averages?: MetricsAverages | null;
  visible: boolean;
}

function formatMs(value: number): string {
  return `${value.toFixed(0)}ms`;
}

function formatNullableMs(value: number | null): string {
  return value !== null ? formatMs(value) : "\u2014";
}

function MetricRow({
  label,
  current,
  average,
}: {
  label: string;
  current: string;
  average: string;
}) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-gray-400">{label}</span>
      <div className="flex gap-3">
        <span className="w-16 text-right">{current}</span>
        <span className="w-16 text-right text-blue-300">{average}</span>
      </div>
    </div>
  );
}

export default function LatencyOverlay({
  metrics,
  averages,
  visible,
}: LatencyOverlayProps) {
  if (!visible) return null;

  const hasData = metrics !== undefined || averages !== undefined;

  return (
    <div className="absolute top-2 right-2 bg-black/80 text-white text-xs p-3 rounded-lg font-mono min-w-[260px] shadow-lg border border-gray-700/50">
      {/* Header with live indicator */}
      <div className="flex items-center justify-between mb-2 pb-1 border-b border-gray-600/50">
        <span className="text-gray-300 font-semibold text-[11px] uppercase tracking-wide">
          Latency Metrics
        </span>
        <div className="flex items-center gap-1.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
          <span className="text-green-400 text-[10px]">LIVE</span>
        </div>
      </div>

      {!hasData ? (
        <p className="text-gray-500 text-center py-1">
          Waiting for first turn&hellip;
        </p>
      ) : (
        <>
          {/* Column headers */}
          <div className="flex justify-between gap-4 mb-1">
            <span className="text-gray-500 text-[10px]">Stage</span>
            <div className="flex gap-3">
              <span className="w-16 text-right text-gray-500 text-[10px]">Current</span>
              <span className="w-16 text-right text-gray-500 text-[10px]">Avg</span>
            </div>
          </div>

          <MetricRow
            label="STT"
            current={metrics ? formatMs(metrics.stt_ms) : "\u2014"}
            average={averages ? formatMs(averages.stt_ms) : "\u2014"}
          />
          <MetricRow
            label="LLM TTFT"
            current={metrics ? formatMs(metrics.llm_ttft_ms) : "\u2014"}
            average={averages ? formatMs(averages.llm_ttft_ms) : "\u2014"}
          />
          <MetricRow
            label="TTS TTFB"
            current={metrics ? formatMs(metrics.tts_ttfb_ms) : "\u2014"}
            average={averages ? formatMs(averages.tts_ttfb_ms) : "\u2014"}
          />
          <MetricRow
            label="Avatar"
            current={metrics ? formatNullableMs(metrics.avatar_render_ms) : "\u2014"}
            average={averages ? formatNullableMs(averages.avatar_render_ms) : "\u2014"}
          />

          {/* Total E2E — highlighted */}
          <div className="flex justify-between gap-4 mt-1 pt-1 border-t border-gray-600/50 font-semibold">
            <span className="text-gray-200">Total E2E</span>
            <div className="flex gap-3">
              <span className="w-16 text-right text-yellow-300">
                {metrics ? formatMs(metrics.total_e2e_ms) : "\u2014"}
              </span>
              <span className="w-16 text-right text-blue-300">
                {averages ? formatMs(averages.total_e2e_ms) : "\u2014"}
              </span>
            </div>
          </div>

          {/* Turn count */}
          {averages && (
            <div className="mt-1 text-[10px] text-gray-500 text-right">
              {averages.turn_count} turn{averages.turn_count !== 1 ? "s" : ""} recorded
            </div>
          )}
        </>
      )}
    </div>
  );
}
