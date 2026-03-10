import { ConnectionState as LKConnectionState } from "livekit-client";
import type { ConnectionState, TurnMetrics } from "./types";
import { createLogger } from "./logger";

const logger = createLogger("livekit");

/**
 * Map LiveKit's internal ConnectionState enum to our app ConnectionState type.
 */
export function mapConnectionState(lkState: LKConnectionState): ConnectionState {
  switch (lkState) {
    case LKConnectionState.Disconnected:
      return "disconnected";
    case LKConnectionState.Connecting:
      return "connecting";
    case LKConnectionState.Connected:
      return "connected";
    case LKConnectionState.Reconnecting:
      return "reconnecting";
    default:
      return "failed";
  }
}

/**
 * Fetch a LiveKit token and server URL from our backend token API.
 * Throws if the response is not OK or if required fields are missing.
 */
export async function getToken(
  subject: string
): Promise<{ token: string; url: string }> {
  logger.info("fetching_token", { subject });

  const response = await fetch(`/api/token?subject=${encodeURIComponent(subject)}`);

  if (!response.ok) {
    const errorText = await response.text().catch(() => "unknown error");
    logger.error("token_fetch_failed", { subject, status: response.status, errorText });
    throw new Error(`Failed to fetch token (${response.status}): ${errorText}`);
  }

  const data: unknown = await response.json();

  if (
    typeof data !== "object" ||
    data === null ||
    typeof (data as Record<string, unknown>).token !== "string" ||
    typeof (data as Record<string, unknown>).url !== "string"
  ) {
    logger.error("token_response_invalid", { subject });
    throw new Error("Invalid token response: missing token or url");
  }

  const { token, url } = data as { token: string; url: string };

  if (!token || !url) {
    logger.warn("token_or_url_empty", { subject });
  }

  logger.info("token_fetched", { subject });
  return { token, url };
}

/**
 * Decode and parse a data channel message from the agent.
 * Returns a TurnMetrics object if the message is valid, or null otherwise.
 */
export function parseMetricsMessage(data: Uint8Array): TurnMetrics | null {
  try {
    const text = new TextDecoder().decode(data);
    const parsed: unknown = JSON.parse(text);

    if (
      typeof parsed !== "object" ||
      parsed === null
    ) {
      return null;
    }

    const obj = parsed as Record<string, unknown>;

    const isValidNumber = (v: unknown): v is number =>
      typeof v === "number" && isFinite(v);

    if (
      !isValidNumber(obj.turn) ||
      !isValidNumber(obj.stt_ms) ||
      !isValidNumber(obj.llm_ttft_ms) ||
      !isValidNumber(obj.tts_ttfb_ms) ||
      !isValidNumber(obj.total_e2e_ms)
    ) {
      logger.warn("metrics_message_invalid_shape", { parsed: text.slice(0, 200) });
      return null;
    }

    return {
      turn: obj.turn,
      stt_ms: obj.stt_ms,
      llm_ttft_ms: obj.llm_ttft_ms,
      tts_ttfb_ms: obj.tts_ttfb_ms,
      total_e2e_ms: obj.total_e2e_ms,
    };
  } catch (err) {
    logger.warn("metrics_message_parse_error", {
      error: err instanceof Error ? err.message : String(err),
    });
    return null;
  }
}
