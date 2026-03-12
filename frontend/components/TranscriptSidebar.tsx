"use client";

import { useEffect, useRef } from "react";

export interface TranscriptEntry {
  id: string;
  role: "user" | "agent";
  text: string;
  timestamp: number;
}

interface TranscriptSidebarProps {
  entries: readonly TranscriptEntry[];
  visible: boolean;
}

function formatTime(ts: number): string {
  const date = new Date(ts);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function TranscriptSidebar({ entries, visible }: TranscriptSidebarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when entries change (new messages or streaming updates)
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [entries]);

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
    </aside>
  );
}
