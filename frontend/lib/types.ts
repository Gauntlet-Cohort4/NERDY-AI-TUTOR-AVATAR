export type Subject =
  | "biology"
  | "math"
  | "earth_science"
  | "intro_algebra"
  | "algebra_ii"
  | "chemistry"
  | "cell_biology"
  | "world_history"
  | "calculus"
  | "physics"
  | "ap_biology";

export interface TurnMetrics {
  turn: number;
  stt_ms: number;
  llm_ttft_ms: number;
  tts_ttfb_ms: number;
  avatar_render_ms: number | null;
  total_e2e_ms: number;
}

export interface SessionSummary {
  session_id: string;
  total_turns: number;
  e2e_mean_ms: number;
  e2e_median_ms: number;
  e2e_p95_ms: number;
  e2e_max_ms: number;
  pct_under_500ms: number;
  pct_under_1000ms: number;
}

export interface MetricsAverages {
  stt_ms: number;
  llm_ttft_ms: number;
  tts_ttfb_ms: number;
  avatar_render_ms: number | null;
  total_e2e_ms: number;
  turn_count: number;
}

export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "failed";
