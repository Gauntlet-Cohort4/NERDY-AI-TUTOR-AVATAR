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

// ── Session & Dashboard Types ────────────────────────────────────────

export interface User {
  id: string;
  display_name: string;
  created_at: string;
}

export interface Session {
  id: string;
  user_id: string;
  subject: Subject;
  grade: number;
  room_name: string;
  started_at: string;
  ended_at: string | null;
  duration_secs: number | null;
  summary_cache: string | null;
  status: "active" | "completed" | "errored";
}

export interface TranscriptTurn {
  id: string;
  session_id: string;
  turn_number: number;
  role: "student" | "tutor";
  content: string;
  metrics: TurnMetrics | null;
  created_at: string;
}

// ── Artifact Types ───────────────────────────────────────────────────

export type ArtifactType = "summary" | "cheat_sheet" | "worksheet" | "review_quiz";
export type ArtifactStatus = "pending" | "generating" | "ready" | "failed";

export interface Artifact {
  id: string;
  session_id: string;
  artifact_type: ArtifactType;
  title: string;
  content_json: Record<string, unknown>;
  status: ArtifactStatus;
  created_at: string;
  updated_at: string;
  has_pdf?: boolean;
}

export interface SummaryContent {
  text: string;
}

export interface CheatSheetContent {
  title: string;
  session_label: string;
  key_concepts: Array<{ term: string; definition: string; example: string }>;
  formulas: Array<{ name: string; latex: string; when_to_use: string }>;
  common_mistakes: string[];
  memory_aids: string[];
  quick_reference_steps: Array<{ step: number; description: string }>;
}

export interface WorksheetContent {
  title: string;
  instructions: string;
  problems: WorksheetProblem[];
  difficulty_distribution: string;
}

export interface WorksheetProblem {
  number: number;
  question: string;
  question_latex: string | null;
  type: "multiple_choice" | "short_answer" | "show_work";
  options: string[] | null;
  answer: string;
  explanation: string;
  difficulty: "easy" | "medium" | "hard";
}

export interface ReviewQuizContent {
  questions: ReviewQuestion[];
}

export interface ReviewQuestion {
  id: string;
  question: string;
  question_latex: string | null;
  type: "multiple_choice" | "short_answer";
  options: string[] | null;
  correct_answer: string;
  accept_also: string[];
  source_turn: number;
  topic: string;
  difficulty: "easy" | "medium" | "hard";
  hint: string;
}

// ── Flash Card Types ─────────────────────────────────────────────────

export type FlashCardMastery = "new" | "learning" | "known";

export interface FlashCard {
  id: string;
  user_id: string;
  subject: Subject;
  term: string;
  definition: string;
  example: string | null;
  grade: number;
  source_session_id: string | null;
  mastery: FlashCardMastery;
  last_reviewed_at: string | null;
  created_at: string;
}

export interface FlashCardStats {
  total: number;
  new: number;
  learning: number;
  known: number;
}

// ── Upload Types ─────────────────────────────────────────────────────

export type UploadStatus = "uploaded" | "processing" | "classified" | "reviewing";

export interface Upload {
  id: string;
  user_id: string;
  session_id: string | null;
  file_name: string;
  file_type: string;
  extracted_text: string | null;
  detected_subject: Subject | null;
  detected_grade: number | null;
  status: UploadStatus;
  created_at: string;
}

export interface ClassificationResult {
  subject: Subject;
  grade: number;
  confidence: number;
  problems_found: Array<{
    number: number;
    question_text: string;
    student_answer: string;
    answer_is_correct: boolean | null;
    topic: string;
  }>;
  overall_topic: string;
  notes: string;
}

// ── Whiteboard Types ─────────────────────────────────────────────────

export type WhiteboardPayloadType = "equation" | "image" | "svg_diagram" | "interactive" | "generating";

export interface WhiteboardPayload {
  type: WhiteboardPayloadType;
  content?: string;
  latex?: string;
  title?: string;
  alt_text?: string;
  template_id?: string;
  params?: Record<string, unknown>;
  description?: string;
}

// ── SSE Event Types ──────────────────────────────────────────────────

export interface ArtifactStatusEvent {
  artifact_type: ArtifactType;
  status: ArtifactStatus;
  count?: number;
}

export interface TokenEvent {
  text: string;
}

export interface DoneEvent {
  full_text: string;
}
