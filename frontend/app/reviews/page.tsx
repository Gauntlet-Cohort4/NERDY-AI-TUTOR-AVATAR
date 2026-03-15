"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { getUserId } from "@/lib/user";
import { listSessions, listArtifacts, downloadArtifactPdf } from "@/lib/api";
import type { Session, Artifact, Subject } from "@/lib/types";
import { createLogger } from "@/lib/logger";

const logger = createLogger("ReviewsPage");

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SessionWithArtifacts {
  readonly session: Session;
  readonly artifacts: readonly Artifact[];
}

type GroupedSessions = ReadonlyMap<Subject, readonly SessionWithArtifacts[]>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function subjectLabel(subject: Subject): string {
  const labels: Record<Subject, string> = {
    biology: "Biology",
    math: "Math",
    earth_science: "Earth Science",
    intro_algebra: "Intro Algebra",
    algebra_ii: "Algebra II",
    chemistry: "Chemistry",
    cell_biology: "Cell Biology",
    world_history: "World History",
    calculus: "Calculus",
    physics: "Physics",
    ap_biology: "AP Biology",
  };
  return labels[subject] ?? subject;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function groupBySubject(
  items: readonly SessionWithArtifacts[]
): GroupedSessions {
  const groups = new Map<Subject, SessionWithArtifacts[]>();
  for (const item of items) {
    const existing = groups.get(item.session.subject) ?? [];
    groups.set(item.session.subject, [...existing, item]);
  }
  return groups;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ArtifactRow({
  artifact,
  sessionId,
  onExpandSummary,
  expandedSummaryId,
}: {
  readonly artifact: Artifact;
  readonly sessionId: string;
  readonly onExpandSummary: (id: string | null) => void;
  readonly expandedSummaryId: string | null;
}) {
  const router = useRouter();
  const [downloading, setDownloading] = useState(false);

  const handleDownloadPdf = useCallback(async () => {
    setDownloading(true);
    try {
      const blob = await downloadArtifactPdf(artifact.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${artifact.title}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      logger.info("pdf_downloaded", { artifactId: artifact.id });
    } catch (err) {
      logger.error("pdf_download_failed", { error: String(err) });
    } finally {
      setDownloading(false);
    }
  }, [artifact.id, artifact.title]);

  const isSummaryExpanded = expandedSummaryId === artifact.id;

  const cj = artifact.content_json;
  const summaryText =
    artifact.artifact_type === "summary" && typeof cj === "object" && cj !== null && typeof (cj as Record<string, unknown>).text === "string"
      ? ((cj as Record<string, unknown>).text as string)
      : "";

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-300 capitalize min-w-[100px]">
          {artifact.artifact_type.replace("_", " ")}
        </span>
        <span className="text-xs text-gray-500">{artifact.title}</span>
        <div className="ml-auto flex gap-2">
          {artifact.artifact_type === "summary" && (
            <button
              onClick={() =>
                onExpandSummary(isSummaryExpanded ? null : artifact.id)
              }
              className="text-xs px-3 py-1 rounded bg-gray-700 text-blue-400 hover:bg-gray-600 transition-colors"
            >
              {isSummaryExpanded ? "Collapse" : "Summary"}
            </button>
          )}
          {artifact.artifact_type === "cheat_sheet" && (
            <button
              onClick={() => router.push(`/reviews/${sessionId}`)}
              className="text-xs px-3 py-1 rounded bg-gray-700 text-blue-400 hover:bg-gray-600 transition-colors"
            >
              Cheat Sheet
            </button>
          )}
          {artifact.artifact_type === "worksheet" && (
            <>
              <button
                onClick={() => router.push(`/worksheet/${artifact.id}`)}
                className="text-xs px-3 py-1 rounded bg-gray-700 text-green-400 hover:bg-gray-600 transition-colors"
              >
                Practice
              </button>
              <button
                onClick={handleDownloadPdf}
                disabled={downloading}
                className="text-xs px-3 py-1 rounded bg-gray-700 text-amber-400 hover:bg-gray-600 transition-colors disabled:opacity-50"
              >
                {downloading ? "..." : "PDF"}
              </button>
            </>
          )}
          {artifact.artifact_type === "review_quiz" && (
            <button
              onClick={() => router.push(`/review-quiz/${sessionId}`)}
              className="text-xs px-3 py-1 rounded bg-gray-700 text-purple-400 hover:bg-gray-600 transition-colors"
            >
              Review Quiz
            </button>
          )}
        </div>
      </div>
      {isSummaryExpanded && summaryText && (
        <div className="text-sm text-gray-400 bg-gray-800 rounded p-3 ml-4 border border-gray-700">
          {summaryText}
        </div>
      )}
    </div>
  );
}

function SessionCard({
  data,
  expandedSummaryId,
  onExpandSummary,
}: {
  readonly data: SessionWithArtifacts;
  readonly expandedSummaryId: string | null;
  readonly onExpandSummary: (id: string | null) => void;
}) {
  const readyArtifacts = data.artifacts.filter((a) => a.status === "ready");

  return (
    <div className="border border-gray-700 rounded-lg p-4 bg-gray-800/40">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-sm font-medium text-white">
          {formatDate(data.session.started_at)}
        </span>
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${
            data.session.status === "completed"
              ? "bg-green-900/40 text-green-400"
              : data.session.status === "active"
                ? "bg-amber-900/40 text-amber-400"
                : "bg-red-900/40 text-red-400"
          }`}
        >
          {data.session.status}
        </span>
        {data.session.duration_secs !== null && (
          <span className="text-xs text-gray-500">
            {Math.round(data.session.duration_secs / 60)} min
          </span>
        )}
      </div>
      {readyArtifacts.length === 0 ? (
        <p className="text-xs text-gray-500">No artifacts available yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {readyArtifacts.map((artifact) => (
            <ArtifactRow
              key={artifact.id}
              artifact={artifact}
              sessionId={data.session.id}
              expandedSummaryId={expandedSummaryId}
              onExpandSummary={onExpandSummary}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ReviewsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [allSessions, setAllSessions] = useState<
    readonly SessionWithArtifacts[]
  >([]);
  const [expandedSummaryId, setExpandedSummaryId] = useState<string | null>(
    null
  );
  const [subjectFilter, setSubjectFilter] = useState<Subject | null>(null);
  const [gradeFilter, setGradeFilter] = useState<number | null>(null);

  useEffect(() => {
    const userId = getUserId();
    if (!userId) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchData() {
      try {
        const sessions = await listSessions(userId!);
        const completedSessions = sessions.filter(
          (s) => s.status === "completed"
        );

        const withArtifacts: SessionWithArtifacts[] = await Promise.all(
          completedSessions.map(async (session) => {
            try {
              const artifacts = await listArtifacts(session.id);
              return { session, artifacts };
            } catch {
              logger.warn("artifacts_fetch_failed", {
                sessionId: session.id,
              });
              return { session, artifacts: [] };
            }
          })
        );

        if (!cancelled) {
          setAllSessions(withArtifacts);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          logger.error("reviews_fetch_failed", { error: String(err) });
          setError("Failed to load session reviews. Please try again.");
          setLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  // Extract unique subjects and grades from loaded sessions
  const uniqueSubjects = useMemo<readonly Subject[]>(
    () =>
      [...new Set(allSessions.map((s) => s.session.subject))].sort(),
    [allSessions]
  );

  const uniqueGrades = useMemo<readonly number[]>(
    () =>
      [...new Set(allSessions.map((s) => s.session.grade))].sort(
        (a, b) => a - b
      ),
    [allSessions]
  );

  // Apply filters (AND logic)
  const filteredSessions = useMemo<readonly SessionWithArtifacts[]>(
    () =>
      allSessions.filter((item) => {
        const matchesSubject =
          subjectFilter === null || item.session.subject === subjectFilter;
        const matchesGrade =
          gradeFilter === null || item.session.grade === gradeFilter;
        return matchesSubject && matchesGrade;
      }),
    [allSessions, subjectFilter, gradeFilter]
  );

  // Group filtered sessions by subject (only when showing all subjects)
  const grouped = useMemo<GroupedSessions>(
    () => groupBySubject(filteredSessions),
    [filteredSessions]
  );

  const hasData = allSessions.length > 0;
  const hasFilteredResults = filteredSessions.length > 0;
  const isFiltering = subjectFilter !== null || gradeFilter !== null;

  return (
    <div className="min-h-screen" style={{ background: "#0a1d37" }}>
      {/* Header */}
      <nav
        className="sticky top-0 z-50 flex items-center justify-between px-10 py-4"
        style={{
          background: "rgba(10,29,55,0.95)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-1 bg-transparent border-none cursor-pointer text-blue-400 text-sm hover:text-blue-300"
            aria-label="Back to Home"
          >
            <span>&larr;</span> Back
          </button>
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2.5 bg-transparent border-none cursor-pointer"
          >
          <div
            className="flex items-center justify-center w-9 h-9 rounded-[10px] text-white text-base font-extrabold"
            style={{
              background: "linear-gradient(135deg, #007AFF, #0056b3)",
            }}
          >
            N
          </div>
          <span
            className="text-white font-bold text-lg"
            style={{ letterSpacing: "-0.02em" }}
          >
            Nerdy AI Tutor
          </span>
        </button>
        </div>
        <span className="text-white/60 text-sm">All Reviews</span>
      </nav>

      {/* Content */}
      <main className="mx-auto px-6 py-10" style={{ maxWidth: 900 }}>
        <h1 className="text-2xl font-bold text-white mb-8">
          Session Reviews
        </h1>

        {/* Filter Controls */}
        {!loading && !error && hasData && (
          <div className="mb-8 flex flex-col gap-4">
            {/* Subject Filter */}
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">
                Subject
              </span>
              <div className="flex gap-2 flex-wrap" role="tablist" aria-label="Filter by subject">
                <button
                  role="tab"
                  aria-selected={subjectFilter === null}
                  onClick={() => setSubjectFilter(null)}
                  className="px-4 py-2 rounded-lg text-sm font-medium border-none cursor-pointer transition-all duration-200"
                  style={{
                    background: subjectFilter === null ? "#007AFF" : "rgba(255,255,255,0.06)",
                    color: subjectFilter === null ? "#fff" : "#6a7f99",
                    fontFamily: "inherit",
                  }}
                >
                  All
                </button>
                {uniqueSubjects.map((subject) => (
                  <button
                    key={subject}
                    role="tab"
                    aria-selected={subjectFilter === subject}
                    onClick={() => setSubjectFilter(subject)}
                    className="px-4 py-2 rounded-lg text-sm font-medium border-none cursor-pointer transition-all duration-200"
                    style={{
                      background: subjectFilter === subject ? "#007AFF" : "rgba(255,255,255,0.06)",
                      color: subjectFilter === subject ? "#fff" : "#6a7f99",
                      fontFamily: "inherit",
                    }}
                  >
                    {subjectLabel(subject)}
                  </button>
                ))}
              </div>
            </div>

            {/* Grade Filter */}
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">
                Grade
              </span>
              <div className="flex gap-2 flex-wrap" role="tablist" aria-label="Filter by grade">
                <button
                  role="tab"
                  aria-selected={gradeFilter === null}
                  onClick={() => setGradeFilter(null)}
                  className="px-4 py-2 rounded-lg text-sm font-medium border-none cursor-pointer transition-all duration-200"
                  style={{
                    background: gradeFilter === null ? "#007AFF" : "rgba(255,255,255,0.06)",
                    color: gradeFilter === null ? "#fff" : "#6a7f99",
                    fontFamily: "inherit",
                  }}
                >
                  All Grades
                </button>
                {uniqueGrades.map((grade) => (
                  <button
                    key={grade}
                    role="tab"
                    aria-selected={gradeFilter === grade}
                    onClick={() => setGradeFilter(grade)}
                    className="px-4 py-2 rounded-lg text-sm font-medium border-none cursor-pointer transition-all duration-200"
                    style={{
                      background: gradeFilter === grade ? "#007AFF" : "rgba(255,255,255,0.06)",
                      color: gradeFilter === grade ? "#fff" : "#6a7f99",
                      fontFamily: "inherit",
                    }}
                  >
                    Grade {grade}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {loading && (
          <div className="text-center py-20">
            <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-400 text-sm">Loading reviews...</p>
          </div>
        )}

        {error && (
          <div className="text-center py-20">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {!loading && !error && !hasData && (
          <div className="text-center py-20">
            <p className="text-gray-400 text-sm mb-4">
              No completed sessions yet. Start a tutoring session to generate
              review materials.
            </p>
            <button
              onClick={() => router.push("/")}
              className="text-blue-400 text-sm hover:text-blue-300 transition-colors"
            >
              Go to Dashboard
            </button>
          </div>
        )}

        {/* Empty state when filters match nothing */}
        {!loading && !error && hasData && !hasFilteredResults && isFiltering && (
          <div className="text-center py-20">
            <p className="text-gray-400 text-sm mb-4">
              No sessions match the selected filters. Try adjusting the subject
              or grade filter.
            </p>
            <button
              onClick={() => {
                setSubjectFilter(null);
                setGradeFilter(null);
              }}
              className="text-blue-400 text-sm hover:text-blue-300 transition-colors"
            >
              Clear Filters
            </button>
          </div>
        )}

        {/* Grouped display (subject = All) */}
        {!loading &&
          !error &&
          hasFilteredResults &&
          subjectFilter === null &&
          Array.from(grouped.entries()).map(([subject, sessions]) => (
            <section key={subject} className="mb-10">
              <h2 className="text-lg font-semibold text-white mb-4">
                {subjectLabel(subject)}
              </h2>
              <div className="flex flex-col gap-4">
                {sessions.map((data) => (
                  <SessionCard
                    key={data.session.id}
                    data={data}
                    expandedSummaryId={expandedSummaryId}
                    onExpandSummary={setExpandedSummaryId}
                  />
                ))}
              </div>
            </section>
          ))}

        {/* Flat display (specific subject selected) */}
        {!loading &&
          !error &&
          hasFilteredResults &&
          subjectFilter !== null && (
            <div className="flex flex-col gap-4">
              {filteredSessions.map((data) => (
                <SessionCard
                  key={data.session.id}
                  data={data}
                  expandedSummaryId={expandedSummaryId}
                  onExpandSummary={setExpandedSummaryId}
                />
              ))}
            </div>
          )}
      </main>
    </div>
  );
}
