import { createLogger } from "./logger";
import type { ArtifactStatusEvent, TokenEvent, DoneEvent } from "./types";

const logger = createLogger("sse");

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8080";

export interface SSECallbacks {
  onArtifactStatus?: (event: ArtifactStatusEvent) => void;
  onToken?: (event: TokenEvent) => void;
  onDone?: (event: DoneEvent) => void;
  onError?: (error: Event) => void;
}

/**
 * Fetch current artifact statuses for a session (one-shot JSON).
 * Returns a cleanup function (no-op, kept for API compatibility).
 */
export function subscribeToArtifactStatus(
  sessionId: string,
  callbacks: Pick<SSECallbacks, "onArtifactStatus" | "onError">
): () => void {
  const url = `${AGENT_URL}/api/sessions/${sessionId}/events`;
  let cancelled = false;

  async function poll() {
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const statuses: Array<{ artifact_type: string; status: string }> =
        await res.json();
      if (cancelled) return;
      for (const data of statuses) {
        logger.debug("artifact_status_received", {
          type: data.artifact_type,
          status: data.status,
        });
        callbacks.onArtifactStatus?.({
          artifact_type: data.artifact_type as ArtifactStatusEvent["artifact_type"],
          status: data.status as ArtifactStatusEvent["status"],
        });
      }
    } catch (err) {
      if (!cancelled) {
        logger.warn("artifact_status_fetch_error", { error: String(err) });
        callbacks.onError?.(new Event("fetch_error"));
      }
    }
  }

  poll();
  return () => {
    cancelled = true;
  };
}

/**
 * Subscribe to a streaming LLM response (review chat, quiz generation).
 * Returns a cleanup function to close the connection.
 */
export function subscribeToStream(
  url: string,
  callbacks: Pick<SSECallbacks, "onToken" | "onDone" | "onError">
): () => void {
  const fullUrl = url.startsWith("http") ? url : `${AGENT_URL}${url}`;
  const source = new EventSource(fullUrl);

  source.addEventListener("token", (e: MessageEvent) => {
    try {
      const data: TokenEvent = JSON.parse(e.data);
      callbacks.onToken?.(data);
    } catch (err) {
      logger.error("token_parse_error", { error: String(err) });
    }
  });

  source.addEventListener("done", (e: MessageEvent) => {
    source.close();
    try {
      const data: DoneEvent = JSON.parse(e.data);
      callbacks.onDone?.(data);
    } catch (err) {
      logger.error("done_parse_error", { error: String(err) });
    }
  });

  source.onerror = (e) => {
    logger.warn("stream_error", { url: fullUrl, readyState: source.readyState });
    if (source.readyState === EventSource.CLOSED) {
      callbacks.onError?.(e);
    }
  };

  return () => {
    source.close();
  };
}

/**
 * Send a message to the review chat and subscribe to streaming response.
 * Uses POST + SSE pattern: POST sends the message, response is SSE stream.
 */
export async function sendReviewMessage(
  uploadId: string,
  message: string,
  callbacks: Pick<SSECallbacks, "onToken" | "onDone" | "onError">
): Promise<() => void> {
  const url = `${AGENT_URL}/api/review/${uploadId}/message`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    throw new Error(`Review message failed: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";
  let cancelled = false;

  (async () => {
    try {
      while (!cancelled) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.text !== undefined && data.full_text === undefined) {
                callbacks.onToken?.({ text: data.text });
              } else if (data.full_text !== undefined) {
                callbacks.onDone?.({ full_text: data.full_text });
              }
            } catch {
              // Skip unparseable lines
            }
          }
        }
      }
    } catch (err) {
      if (!cancelled) {
        callbacks.onError?.(new Event("stream_error"));
      }
    }
  })();

  return () => {
    cancelled = true;
    reader.cancel();
  };
}
