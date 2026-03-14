import { createLogger } from "./logger";
import { subscribeToStream } from "./sse";
import type {
  Session,
  TranscriptTurn,
  Artifact,
  FlashCard,
  FlashCardMastery,
  FlashCardStats,
  Upload,
  Subject,
} from "./types";

const logger = createLogger("api");

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8080";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${AGENT_URL}${path}`;
  logger.debug("api_request", { method: options?.method || "GET", path });
  const res = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const rawError = await res.text().catch(() => "Unknown error");
    const errorText = rawError.slice(0, 200);
    logger.error("api_error", { path, status: res.status, error: errorText });
    throw new Error(`API error ${res.status}: ${errorText}`);
  }
  return res.json();
}

// Sessions

export async function listSessions(
  userId: string,
  subject?: Subject
): Promise<Session[]> {
  const params = new URLSearchParams({ user_id: userId });
  if (subject) params.set("subject", subject);
  return fetchJSON(`/api/sessions?${params}`);
}

export async function getSession(sessionId: string): Promise<Session> {
  return fetchJSON(`/api/sessions/${sessionId}`);
}

export async function getSessionTranscript(
  sessionId: string
): Promise<TranscriptTurn[]> {
  return fetchJSON(`/api/sessions/${sessionId}/transcript`);
}

// Artifacts

export async function listArtifacts(sessionId: string): Promise<Artifact[]> {
  return fetchJSON(`/api/sessions/${sessionId}/artifacts`);
}

export async function getArtifact(artifactId: string): Promise<Artifact> {
  return fetchJSON(`/api/artifacts/${artifactId}`);
}

export async function downloadArtifactPdf(artifactId: string): Promise<Blob> {
  const url = `${AGENT_URL}/api/artifacts/${artifactId}/pdf`;
  logger.debug("pdf_download_request", { artifactId });
  const res = await fetch(url);
  if (!res.ok) {
    logger.error("pdf_download_failed", { artifactId, status: res.status });
    throw new Error(`PDF download failed: ${res.status}`);
  }
  return res.blob();
}

// Flash Cards

export async function listFlashCards(
  userId: string,
  subject?: Subject
): Promise<FlashCard[]> {
  const params = new URLSearchParams({ user_id: userId });
  if (subject) params.set("subject", subject);
  return fetchJSON(`/api/flash-cards?${params}`);
}

export async function updateFlashCardMastery(
  cardId: string,
  mastery: FlashCardMastery
): Promise<void> {
  await fetchJSON(`/api/flash-cards/${cardId}`, {
    method: "PATCH",
    body: JSON.stringify({ mastery }),
  });
}

export async function getFlashCardStats(
  userId: string
): Promise<Record<string, FlashCardStats>> {
  const params = new URLSearchParams({ user_id: userId });
  return fetchJSON(`/api/flash-cards/stats?${params}`);
}

export async function generateFlashCards(
  sessionId: string,
  userId: string
): Promise<FlashCard[]> {
  const result = await fetchJSON<{ flash_cards: FlashCard[] }>(
    `/api/sessions/${sessionId}/flash-cards`,
    {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }
  );
  return result.flash_cards;
}

// Uploads

export async function uploadFile(
  userId: string,
  file: File,
  sessionId?: string
): Promise<Upload> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", userId);
  if (sessionId) formData.append("session_id", sessionId);

  const url = `${AGENT_URL}/api/uploads`;
  const res = await fetch(url, { method: "POST", body: formData });
  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function getUpload(uploadId: string): Promise<Upload> {
  return fetchJSON(`/api/uploads/${uploadId}`);
}

// Review Quiz

/**
 * Start a review quiz SSE stream. Returns a cleanup function.
 * The caller MUST call the cleanup function when done to avoid connection leaks.
 */
export function startReviewQuiz(
  sessionId: string,
  callbacks: { onToken?: (e: { text: string }) => void; onDone?: (e: { full_text: string }) => void; onError?: (e: Event) => void }
): () => void {
  return subscribeToStream(`/api/sessions/${sessionId}/review-quiz`, callbacks);
}

export async function submitQuizAnswers(
  sessionId: string,
  answers: Record<string, string>
): Promise<{
  score: number;
  total: number;
  results: Array<{ id: string; correct: boolean; correct_answer: string }>;
}> {
  return fetchJSON(`/api/sessions/${sessionId}/review-quiz/check`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

// Review Chat

/**
 * Start a review chat SSE stream. Returns a cleanup function.
 * The caller MUST call the cleanup function when done to avoid connection leaks.
 */
export function startReviewChat(
  uploadId: string,
  callbacks: { onToken?: (e: { text: string }) => void; onDone?: (e: { full_text: string }) => void; onError?: (e: Event) => void }
): () => void {
  return subscribeToStream(`/api/review/${uploadId}/start`, callbacks);
}

export async function getReviewHistory(
  uploadId: string
): Promise<Array<{ role: string; content: string }>> {
  return fetchJSON(`/api/review/${uploadId}/history`);
}
