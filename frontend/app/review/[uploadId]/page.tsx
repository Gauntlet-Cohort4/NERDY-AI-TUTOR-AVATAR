"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { createLogger } from "@/lib/logger";
import { getUserId } from "@/lib/user";
import { getUpload, getReviewHistory, startReviewChat } from "@/lib/api";
import { sendReviewMessage } from "@/lib/sse";
import ToastNotification from "@/components/ToastNotification";
import type { Toast } from "@/components/ToastNotification";
import type { Upload } from "@/lib/types";

const logger = createLogger("ReviewChatPage");

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatMessage {
  readonly id: string;
  readonly role: "student" | "tutor";
  readonly content: string;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SubjectBadge({ upload }: { readonly upload: Upload }) {
  const subjectLabel = upload.detected_subject
    ? upload.detected_subject.replace(/_/g, " ")
    : "Unknown";
  const gradeLabel = upload.detected_grade ? `Grade ${upload.detected_grade}` : "";

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-900/40 text-blue-300 border border-blue-700/50 capitalize">
        {subjectLabel}
      </span>
      {gradeLabel && (
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-purple-900/40 text-purple-300 border border-purple-700/50">
          {gradeLabel}
        </span>
      )}
    </div>
  );
}

function MessageBubble({ message }: { readonly message: ChatMessage }) {
  const isTutor = message.role === "tutor";

  return (
    <div
      className={`flex ${isTutor ? "justify-start" : "justify-end"} mb-3`}
    >
      <div
        className="max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
        style={{
          background: isTutor
            ? "rgba(255,255,255,0.06)"
            : "linear-gradient(135deg, #007AFF, #0056b3)",
          color: "#fff",
          borderBottomLeftRadius: isTutor ? 4 : 16,
          borderBottomRightRadius: isTutor ? 16 : 4,
        }}
      >
        <p className="text-xs font-semibold mb-1 opacity-60">
          {isTutor ? "Tutor" : "You"}
        </p>
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-3">
      <div
        className="rounded-2xl px-4 py-3 flex items-center gap-1.5"
        style={{ background: "rgba(255,255,255,0.06)" }}
      >
        <span
          className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: "0ms" }}
        />
        <span
          className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: "150ms" }}
        />
        <span
          className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: "300ms" }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ReviewChatPage() {
  const params = useParams();
  const router = useRouter();
  const uploadId = typeof params.uploadId === "string" ? params.uploadId : "";

  const [upload, setUpload] = useState<Upload | null>(null);
  const [messages, setMessages] = useState<readonly ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [loading, setLoading] = useState(true);
  const [toasts, setToasts] = useState<readonly Toast[]>([]);

  const streamBufferRef = useRef("");
  const cleanupRef = useRef<(() => void) | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  useEffect(() => {
    setUserId(getUserId());
  }, []);

  const addToast = useCallback((message: string, type: Toast["type"]) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  // Clean up SSE on unmount
  useEffect(() => {
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = null;
      }
    };
  }, []);

  // Load upload info and start initial review
  useEffect(() => {
    if (!uploadId || !userId) return;

    let cancelled = false;

    async function initialize() {
      try {
        const uploadData = await getUpload(uploadId);
        if (cancelled) return;

        if (
          typeof uploadData === "object" &&
          uploadData !== null &&
          typeof uploadData.id === "string"
        ) {
          setUpload(uploadData);
        }

        // Load existing history
        try {
          const history = await getReviewHistory(uploadId);
          if (cancelled) return;

          if (Array.isArray(history) && history.length > 0) {
            const loadedMessages: ChatMessage[] = history
              .filter(
                (h): h is { role: string; content: string } =>
                  typeof h === "object" &&
                  h !== null &&
                  typeof h.role === "string" &&
                  typeof h.content === "string",
              )
              .map((h) => ({
                id: crypto.randomUUID(),
                role: h.role === "student" ? "student" : "tutor",
                content: h.content,
              }));
            setMessages(loadedMessages);
            setLoading(false);
            return;
          }
        } catch {
          logger.debug("no_existing_history", { uploadId });
        }

        // No history — start fresh review
        setLoading(false);
        setStreaming(true);
        streamBufferRef.current = "";

        const cleanup = startReviewChat(uploadId, {
          onToken: (event) => {
            if (cancelled) return;
            streamBufferRef.current += event.text;
            setMessages((prev) => {
              const last = prev.length > 0 ? prev[prev.length - 1] : null;
              if (last && last.role === "tutor" && last.id === "streaming") {
                return [
                  ...prev.slice(0, -1),
                  { ...last, content: streamBufferRef.current },
                ];
              }
              return [
                ...prev,
                {
                  id: "streaming",
                  role: "tutor",
                  content: streamBufferRef.current,
                },
              ];
            });
          },
          onDone: (event) => {
            if (cancelled) return;
            setStreaming(false);
            setMessages((prev) => {
              const withoutStreaming = prev.filter((m) => m.id !== "streaming");
              return [
                ...withoutStreaming,
                {
                  id: crypto.randomUUID(),
                  role: "tutor",
                  content: event.full_text,
                },
              ];
            });
          },
          onError: () => {
            if (cancelled) return;
            setStreaming(false);
            addToast("Failed to start review. Please try again.", "error");
          },
        });
        if (cleanupRef.current) cleanupRef.current();
        cleanupRef.current = cleanup;
      } catch (err) {
        if (!cancelled) {
          logger.error("review_init_failed", { error: String(err) });
          setLoading(false);
          addToast("Failed to load review data.", "error");
        }
      }
    }

    initialize();

    return () => {
      cancelled = true;
    };
  }, [uploadId, userId, addToast]);

  const handleSendMessage = useCallback(async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || streaming || !uploadId) return;

    const studentMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "student",
      content: trimmed,
    };

    setMessages((prev) => [...prev, studentMessage]);
    setInputValue("");
    setStreaming(true);
    streamBufferRef.current = "";

    try {
      const cleanup = await sendReviewMessage(uploadId, trimmed, {
        onToken: (event) => {
          streamBufferRef.current += event.text;
          setMessages((prev) => {
            const last = prev.length > 0 ? prev[prev.length - 1] : null;
            if (last && last.role === "tutor" && last.id === "streaming") {
              return [
                ...prev.slice(0, -1),
                { ...last, content: streamBufferRef.current },
              ];
            }
            return [
              ...prev,
              {
                id: "streaming",
                role: "tutor",
                content: streamBufferRef.current,
              },
            ];
          });
        },
        onDone: (event) => {
          setStreaming(false);
          setMessages((prev) => {
            const withoutStreaming = prev.filter((m) => m.id !== "streaming");
            return [
              ...withoutStreaming,
              {
                id: crypto.randomUUID(),
                role: "tutor",
                content: event.full_text,
              },
            ];
          });
        },
        onError: () => {
          setStreaming(false);
          addToast("Message failed to send. Please try again.", "error");
        },
      });
      if (cleanupRef.current) cleanupRef.current();
      cleanupRef.current = cleanup;
    } catch (err) {
      logger.error("send_message_failed", { error: String(err) });
      setStreaming(false);
      addToast("Failed to send message.", "error");
    }
  }, [inputValue, streaming, uploadId, addToast]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage],
  );

  const handleLoadHistory = useCallback(async () => {
    if (!uploadId) return;
    try {
      const history = await getReviewHistory(uploadId);
      if (Array.isArray(history)) {
        const loadedMessages: ChatMessage[] = history
          .filter(
            (h): h is { role: string; content: string } =>
              typeof h === "object" &&
              h !== null &&
              typeof h.role === "string" &&
              typeof h.content === "string",
          )
          .map((h) => ({
            id: crypto.randomUUID(),
            role: h.role === "student" ? "student" : "tutor",
            content: h.content,
          }));
        setMessages(loadedMessages);
        addToast("History loaded.", "info");
      }
    } catch (err) {
      logger.error("load_history_failed", { error: String(err) });
      addToast("Failed to load history.", "error");
    }
  }, [uploadId, addToast]);

  if (!userId) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0a1d37" }}>
        <div className="text-center max-w-md px-6">
          <h2 className="text-white text-xl font-bold mb-2">Session Required</h2>
          <p className="text-sm mb-6" style={{ color: "#6a7f99" }}>
            Start a tutoring session first.
          </p>
          <button
            onClick={() => router.push("/")}
            className="text-white border-none cursor-pointer font-semibold rounded-xl px-6 py-3 text-sm"
            style={{
              background: "linear-gradient(135deg, #007AFF, #0056b3)",
              fontFamily: "inherit",
            }}
          >
            Go to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "#0a1d37" }}>
      {/* Header */}
      <nav
        className="sticky top-0 z-50 flex items-center justify-between px-6 py-3"
        style={{
          background: "rgba(10,29,55,0.95)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/upload")}
            className="text-sm font-medium bg-transparent border-none cursor-pointer flex items-center gap-1.5"
            style={{ color: "#007AFF", fontFamily: "inherit" }}
            aria-label="Back to upload page"
          >
            <span>&larr;</span> Back
          </button>
          {upload && <SubjectBadge upload={upload} />}
        </div>
        <button
          onClick={handleLoadHistory}
          className="text-white/70 text-sm font-medium px-4 py-2 rounded-lg hover:text-white hover:bg-white/5 transition-colors bg-transparent border-none cursor-pointer"
          style={{ fontFamily: "inherit" }}
          aria-label="View conversation history"
        >
          View History
        </button>
      </nav>

      {/* Chat messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-6" style={{ maxWidth: 800, margin: "0 auto", width: "100%" }}>
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div
              className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: "#007AFF", borderTopColor: "transparent" }}
            />
            <span className="ml-3 text-sm" style={{ color: "#6a7f99" }}>
              Loading review...
            </span>
          </div>
        )}

        {!loading && messages.length === 0 && !streaming && (
          <div className="text-center py-12">
            <p className="text-sm" style={{ color: "#6a7f99" }}>
              Starting review analysis...
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {streaming && messages[messages.length - 1]?.id !== "streaming" && (
          <TypingIndicator />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div
        className="sticky bottom-0 px-6 py-4"
        style={{
          background: "rgba(10,29,55,0.95)",
          backdropFilter: "blur(12px)",
          borderTop: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <div className="flex gap-3 mx-auto" style={{ maxWidth: 800 }}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            maxLength={2000}
            placeholder={streaming ? "Tutor is responding..." : "Ask a question about your worksheet..."}
            disabled={streaming}
            aria-label="Type your message"
            className="flex-1 rounded-xl px-4 py-3 text-sm text-white border-none outline-none placeholder:text-gray-500 disabled:opacity-50"
            style={{
              background: "rgba(255,255,255,0.06)",
              fontFamily: "inherit",
            }}
          />
          <button
            onClick={handleSendMessage}
            disabled={streaming || !inputValue.trim()}
            aria-label="Send message"
            className="rounded-xl px-5 py-3 text-white text-sm font-semibold border-none cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
            style={{
              background: "linear-gradient(135deg, #007AFF, #0056b3)",
              fontFamily: "inherit",
            }}
          >
            Send
          </button>
        </div>
      </div>

      <ToastNotification toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
