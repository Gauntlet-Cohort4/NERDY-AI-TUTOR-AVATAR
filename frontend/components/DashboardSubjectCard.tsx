"use client";

import { useRouter } from "next/navigation";
import type { Subject, Session } from "@/lib/types";

interface DashboardSubjectCardProps {
  readonly subject: Subject;
  readonly label: string;
  readonly grade: number;
  readonly sessions: readonly Session[];
}

export default function DashboardSubjectCard({
  subject,
  label,
  grade,
  sessions,
}: DashboardSubjectCardProps) {
  const router = useRouter();
  const completedSessions = sessions.filter((s) => s.status === "completed");
  const hasReviews = completedSessions.length > 0;
  const generatingCount = sessions.filter((s) => s.status === "active").length;

  return (
    <button
      onClick={() => {
        const params = new URLSearchParams({ subject, grade: String(grade) });
        router.push(`/session?${params}`);
      }}
      className="group relative flex flex-col items-center gap-3 rounded-xl border border-gray-700 bg-gray-800/60 p-6 transition-all hover:border-blue-500 hover:bg-gray-800"
    >
      <h3 className="text-lg font-semibold text-white">{label}</h3>
      <p className="text-xs text-gray-400">Grade {grade}</p>

      {hasReviews && (
        <div className="flex items-center gap-1.5 mt-1">
          <span className="w-2 h-2 rounded-full bg-green-400" />
          <span className="text-xs text-green-400">
            {completedSessions.length} review
            {completedSessions.length !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {generatingCount > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span className="text-xs text-amber-400">Generating...</span>
        </div>
      )}
    </button>
  );
}
