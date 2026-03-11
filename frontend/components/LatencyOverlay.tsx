import type { TurnMetrics } from "@/lib/types";

interface LatencyOverlayProps {
  metrics?: TurnMetrics;
}

export default function LatencyOverlay({ metrics }: LatencyOverlayProps) {
  if (!metrics) return null;

  return (
    <div className="absolute top-2 right-2 bg-black/70 text-white text-xs p-2 rounded font-mono">
      <div>STT: {metrics.stt_ms.toFixed(0)}ms</div>
      <div>LLM TTFT: {metrics.llm_ttft_ms.toFixed(0)}ms</div>
      <div>TTS TTFB: {metrics.tts_ttfb_ms.toFixed(0)}ms</div>
      <div>Avatar: {metrics.avatar_render_ms !== null ? `${metrics.avatar_render_ms.toFixed(0)}ms` : "—"}</div>
      <div>Total E2E: {metrics.total_e2e_ms.toFixed(0)}ms</div>
    </div>
  );
}
