"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getSession, listArtifacts } from "@/lib/api";
import type {
  Session,
  Artifact,
  SummaryContent,
  CheatSheetContent,
  WorksheetContent,
} from "@/lib/types";
import ReactMarkdown from "react-markdown";
import { createLogger } from "@/lib/logger";

const logger = createLogger("SessionDetailPage");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function parseSummary(artifact: Artifact): SummaryContent | null {
  const c = artifact.content_json;
  if (typeof c === "object" && c !== null && typeof (c as Record<string, unknown>).text === "string") {
    return c as unknown as SummaryContent;
  }
  return null;
}

function parseCheatSheet(artifact: Artifact): CheatSheetContent | null {
  const c = artifact.content_json;
  if (typeof c === "object" && c !== null && typeof (c as Record<string, unknown>).title === "string" && Array.isArray((c as Record<string, unknown>).key_concepts)) {
    return c as unknown as CheatSheetContent;
  }
  return null;
}

function parseWorksheet(artifact: Artifact): WorksheetContent | null {
  const c = artifact.content_json;
  if (typeof c === "object" && c !== null && typeof (c as Record<string, unknown>).title === "string" && Array.isArray((c as Record<string, unknown>).problems)) {
    return c as unknown as WorksheetContent;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LatexFormula({ latex }: { readonly latex: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    import("katex")
      .then((katex) => {
        if (ref.current) {
          katex.default.render(latex, ref.current, {
            throwOnError: false,
            displayMode: true,
          });
        }
      })
      .catch(() => {
        setFallback(true);
      });
  }, [latex]);

  if (fallback) {
    return (
      <div className="text-gray-300 text-sm mt-1 font-mono bg-gray-900 rounded px-2 py-1 inline-block">
        {latex}
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className="text-gray-300 text-sm mt-1 bg-gray-900 rounded px-3 py-2 overflow-x-auto"
    />
  );
}

function SummarySection({ content }: { readonly content: SummaryContent }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-white mb-3">Session Summary</h2>
      <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-5 prose prose-sm prose-invert max-w-none">
        <ReactMarkdown>{content.text}</ReactMarkdown>
      </div>
    </section>
  );
}

function CheatSheetSection({
  content,
}: {
  readonly content: CheatSheetContent;
}) {
  return (
    <section id="cheat-sheet" className="mb-8 scroll-mt-20">
      <h2 className="text-lg font-semibold text-white mb-3">
        {content.title || "Cheat Sheet"}
      </h2>
      <div className="space-y-6">
        {/* Key Concepts */}
        {content.key_concepts.length > 0 && (
          <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-5">
            <h3 className="text-sm font-semibold text-blue-400 mb-3 uppercase tracking-wider">
              Key Concepts
            </h3>
            <div className="space-y-3">
              {content.key_concepts.map((concept, i) => (
                <div key={i} className="border-b border-gray-700 pb-3 last:border-0 last:pb-0">
                  <span className="text-white font-medium text-sm">
                    {concept.term}
                  </span>
                  <p className="text-gray-400 text-sm mt-1">
                    {concept.definition}
                  </p>
                  {concept.example && (
                    <p className="text-gray-500 text-xs mt-1 italic">
                      Example: {concept.example}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Formulas */}
        {content.formulas.length > 0 && (
          <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-5">
            <h3 className="text-sm font-semibold text-green-400 mb-3 uppercase tracking-wider">
              Formulas
            </h3>
            <div className="space-y-3">
              {content.formulas.map((formula, i) => (
                <div key={i} className="border-b border-gray-700 pb-3 last:border-0 last:pb-0">
                  <span className="text-white font-medium text-sm">
                    {formula.name}
                  </span>
                  <LatexFormula latex={formula.latex} />
                  <p className="text-gray-500 text-xs mt-1">
                    {formula.when_to_use}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Common Mistakes */}
        {content.common_mistakes.length > 0 && (
          <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-5">
            <h3 className="text-sm font-semibold text-red-400 mb-3 uppercase tracking-wider">
              Common Mistakes
            </h3>
            <ul className="space-y-2">
              {content.common_mistakes.map((mistake, i) => (
                <li key={i} className="text-gray-300 text-sm flex gap-2">
                  <span className="text-red-400 shrink-0">!</span>
                  {mistake}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Memory Aids */}
        {content.memory_aids.length > 0 && (
          <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-5">
            <h3 className="text-sm font-semibold text-purple-400 mb-3 uppercase tracking-wider">
              Memory Aids
            </h3>
            <ul className="space-y-2">
              {content.memory_aids.map((aid, i) => (
                <li key={i} className="text-gray-300 text-sm">
                  {aid}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Quick Reference Steps */}
        {content.quick_reference_steps.length > 0 && (
          <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-5">
            <h3 className="text-sm font-semibold text-amber-400 mb-3 uppercase tracking-wider">
              Quick Reference
            </h3>
            <ol className="space-y-2">
              {content.quick_reference_steps.map((step) => (
                <li key={step.step} className="text-gray-300 text-sm flex gap-2">
                  <span className="text-amber-400 font-medium shrink-0">
                    {step.step}.
                  </span>
                  {step.description}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </section>
  );
}

function WorksheetPreview({
  content,
  artifactId,
}: {
  readonly content: WorksheetContent;
  readonly artifactId: string;
}) {
  const router = useRouter();

  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-white mb-3">
        {content.title || "Worksheet"}
      </h2>
      <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-5">
        <p className="text-gray-400 text-sm mb-4">{content.instructions}</p>
        <p className="text-gray-500 text-sm mb-4">
          {content.problems.length} problems ({content.difficulty_distribution})
        </p>
        <button
          onClick={() => router.push(`/worksheet/${artifactId}`)}
          className="text-sm px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-500 transition-colors"
        >
          Start Interactive Worksheet
        </button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = typeof params.sessionId === "string" ? params.sessionId : null;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [artifacts, setArtifacts] = useState<readonly Artifact[]>([]);

  useEffect(() => {
    if (!sessionId) return;
    const sid = sessionId;
    let cancelled = false;

    async function fetchData() {
      try {
        const [sessionData, artifactsData] = await Promise.all([
          getSession(sid),
          listArtifacts(sid),
        ]);
        if (!cancelled) {
          setSession(sessionData);
          setArtifacts(artifactsData.filter((a) => a.status === "ready"));
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          logger.error("session_detail_fetch_failed", {
            error: String(err),
          });
          setError("Failed to load session details.");
          setLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const summaryArtifact = artifacts.find(
    (a) => a.artifact_type === "summary"
  );
  const cheatSheetArtifact = artifacts.find(
    (a) => a.artifact_type === "cheat_sheet"
  );
  const worksheetArtifact = artifacts.find(
    (a) => a.artifact_type === "worksheet"
  );

  const summary = summaryArtifact ? parseSummary(summaryArtifact) : null;
  const cheatSheet = cheatSheetArtifact
    ? parseCheatSheet(cheatSheetArtifact)
    : null;
  const worksheet = worksheetArtifact
    ? parseWorksheet(worksheetArtifact)
    : null;

  if (!sessionId) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0a1d37" }}>
        <p className="text-red-400 text-sm">Invalid session ID.</p>
      </div>
    );
  }

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
        <button
          onClick={() => router.push("/reviews")}
          className="flex items-center gap-2 bg-transparent border-none cursor-pointer text-blue-400 text-sm hover:text-blue-300"
        >
          <span>&larr;</span> Back to Reviews
        </button>
        {session && (
          <span className="text-white/60 text-sm">
            {formatDate(session.started_at)}
          </span>
        )}
      </nav>

      {/* Content */}
      <main className="mx-auto px-6 py-10" style={{ maxWidth: 800 }}>
        {loading && (
          <div className="text-center py-20">
            <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-400 text-sm">Loading session...</p>
          </div>
        )}

        {error && (
          <div className="text-center py-20">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {!loading && !error && session && (
          <>
            <h1 className="text-2xl font-bold text-white mb-2">
              Session Review
            </h1>
            <p className="text-gray-500 text-sm mb-8">
              Grade {session.grade} &middot;{" "}
              {session.subject.replace(/_/g, " ")}
              {session.duration_secs !== null && (
                <> &middot; {Math.round(session.duration_secs / 60)} min</>
              )}
            </p>

            {summary && <SummarySection content={summary} />}
            {cheatSheet && <CheatSheetSection content={cheatSheet} />}
            {worksheet && worksheetArtifact && (
              <WorksheetPreview
                content={worksheet}
                artifactId={worksheetArtifact.id}
              />
            )}
            <section className="mb-8">
              <button
                onClick={() => router.push(`/reviews/${sessionId}/flash-cards`)}
                className="w-full text-left bg-gray-800/60 border border-gray-700 rounded-lg p-5 hover:border-purple-500/40 transition-colors cursor-pointer"
              >
                <h2 className="text-lg font-semibold text-white mb-1">Flash Cards</h2>
                <p className="text-gray-400 text-sm">
                  Study key terms and concepts from this session
                </p>
              </button>
            </section>

            {artifacts.length === 0 && (
              <p className="text-gray-500 text-sm text-center py-10">
                No artifacts available for this session.
              </p>
            )}

          </>
        )}
      </main>
    </div>
  );
}
