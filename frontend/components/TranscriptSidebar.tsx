"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface TranscriptEntry {
  id: string;
  role: "user" | "agent";
  text: string;
  timestamp: number;
}

interface TranscriptSidebarProps {
  entries: readonly TranscriptEntry[];
  visible: boolean;
  onSendMessage?: (text: string) => void;
  isConnected?: boolean;
}

function formatTime(ts: number): string {
  const date = new Date(ts);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function TranscriptSidebar({
  entries,
  visible,
  onSendMessage,
  isConnected = false,
}: TranscriptSidebarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [inputText, setInputText] = useState("");

  // Auto-scroll to bottom when entries change (new messages or streaming updates)
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [entries]);

  const handleSend = useCallback(() => {
    const trimmed = inputText.trim();
    if (!trimmed || !onSendMessage) return;
    onSendMessage(trimmed);
    setInputText("");
    inputRef.current?.focus();
  }, [inputText, onSendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  if (!visible) return null;

  return (
    <aside className="w-80 flex-shrink-0 flex flex-col bg-gray-900 border-l border-gray-800 h-screen sticky top-0">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between flex-shrink-0">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
          Transcript
        </h2>
        <span className="text-[10px] text-gray-500">
          {entries.length} message{entries.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto min-h-0 px-3 py-2 space-y-3"
      >
        {entries.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-4">
            Conversation will appear here&hellip;
          </p>
        ) : (
          entries.map((entry) => (
            <div key={entry.id} className="flex flex-col gap-0.5">
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] font-semibold uppercase tracking-wider ${
                    entry.role === "user" ? "text-blue-400" : "text-green-400"
                  }`}
                >
                  {entry.role === "user" ? "Student" : "Tutor"}
                </span>
                <span className="text-[10px] text-gray-600">{formatTime(entry.timestamp)}</span>
              </div>
              <p
                className={`text-sm leading-relaxed rounded-lg px-3 py-2 ${
                  entry.role === "user"
                    ? "bg-blue-900/30 text-blue-100"
                    : "bg-gray-800 text-gray-200"
                }`}
              >
                {entry.text}
              </p>
            </div>
          ))
        )}
      </div>

      {/* Text input for typing messages (accessible alternative to mic) */}
      {onSendMessage && (
        <div className="px-3 py-3 border-t border-gray-800 flex-shrink-0">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!isConnected}
              placeholder={isConnected ? "Type a message…" : "Connect to chat"}
              className="flex-1 bg-gray-800 text-gray-200 text-sm rounded-lg px-3 py-2
                         border border-gray-700 focus:border-blue-500 focus:outline-none
                         placeholder:text-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Type a message to the tutor"
            />
            <button
              onClick={handleSend}
              disabled={!isConnected || !inputText.trim()}
              className="px-3 py-2 bg-blue-600 text-white text-sm rounded-lg
                         hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed
                         transition-colors"
              aria-label="Send message"
            >
              Send
            </button>
          </div>
          <p className="text-[10px] text-gray-600 mt-1.5 px-1">
            Press Enter to send — use this if you can&apos;t use your mic
          </p>
        </div>
      )}
    </aside>
  );
}
