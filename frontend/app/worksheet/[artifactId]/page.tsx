"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { getArtifact, downloadArtifactPdf } from "@/lib/api";
import type { Artifact, WorksheetContent, WorksheetProblem } from "@/lib/types";
import { createLogger } from "@/lib/logger";

const logger = createLogger("WorksheetPage");

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProgressDots({
  total,
  current,
  answers,
}: {
  readonly total: number;
  readonly current: number;
  readonly answers: ReadonlyMap<number, AnswerResult>;
}) {
  return (
    <div className="flex gap-1.5 justify-center mb-6 flex-wrap">
      {Array.from({ length: total }, (_, i) => {
        const result = answers.get(i);
        const isCurrent = i === current;
        let bg = "bg-gray-600";
        if (result?.correct === true) bg = "bg-green-400";
        else if (result?.correct === false) bg = "bg-red-400";
        else if (isCurrent) bg = "bg-blue-400";

        return (
          <span
            key={i}
            className={`w-3 h-3 rounded-full ${bg} ${isCurrent ? "ring-2 ring-blue-300" : ""}`}
          />
        );
      })}
    </div>
  );
}

function MultipleChoiceInput({
  options,
  selected,
  onSelect,
  disabled,
  correctAnswer,
  submitted,
}: {
  readonly options: readonly string[];
  readonly selected: string;
  readonly onSelect: (val: string) => void;
  readonly disabled: boolean;
  readonly correctAnswer: string;
  readonly submitted: boolean;
}) {
  return (
    <div className="space-y-2">
      {options.map((option, i) => {
        const letter = String.fromCharCode(65 + i);
        const isSelected = selected === letter;
        const isCorrect = submitted && letter === correctAnswer;
        const isWrong = submitted && isSelected && letter !== correctAnswer;

        let borderClass = "border-gray-600";
        if (isCorrect) borderClass = "border-green-400";
        else if (isWrong) borderClass = "border-red-400";
        else if (isSelected && !submitted) borderClass = "border-blue-400";

        return (
          <button
            key={i}
            onClick={() => onSelect(letter)}
            disabled={disabled}
            className={`w-full text-left px-4 py-3 rounded-lg border ${borderClass} bg-gray-800/60 text-sm text-gray-200 hover:border-blue-400 transition-colors disabled:cursor-not-allowed flex gap-3 items-start`}
          >
            <span className="font-medium text-gray-400 shrink-0">
              {letter}.
            </span>
            <span>{option}</span>
          </button>
        );
      })}
    </div>
  );
}

function ShortAnswerInput({
  value,
  onChange,
  disabled,
}: {
  readonly value: string;
  readonly onChange: (val: string) => void;
  readonly disabled: boolean;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      placeholder="Type your answer..."
      className="w-full px-4 py-3 rounded-lg border border-gray-600 bg-gray-800/60 text-sm text-white placeholder-gray-500 focus:border-blue-400 focus:outline-none disabled:cursor-not-allowed"
    />
  );
}

function ShowWorkInput({
  value,
  onChange,
  disabled,
}: {
  readonly value: string;
  readonly onChange: (val: string) => void;
  readonly disabled: boolean;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      placeholder="Show your work here..."
      rows={4}
      className="w-full px-4 py-3 rounded-lg border border-gray-600 bg-gray-800/60 text-sm text-white placeholder-gray-500 focus:border-blue-400 focus:outline-none resize-y disabled:cursor-not-allowed"
    />
  );
}

function ScoreSummary({
  correct,
  total,
  onRestart,
  onDownloadPdf,
  downloading,
}: {
  readonly correct: number;
  readonly total: number;
  readonly onRestart: () => void;
  readonly onDownloadPdf: () => void;
  readonly downloading: boolean;
}) {
  const pct = total > 0 ? Math.round((correct / total) * 100) : 0;
  const color = pct >= 80 ? "text-green-400" : pct >= 50 ? "text-amber-400" : "text-red-400";

  return (
    <div className="text-center py-10">
      <h2 className="text-2xl font-bold text-white mb-2">Worksheet Complete</h2>
      <p className={`text-4xl font-extrabold ${color} mb-2`}>
        {correct}/{total}
      </p>
      <p className="text-gray-400 text-sm mb-8">{pct}% correct</p>
      <div className="flex gap-4 justify-center">
        <button
          onClick={onRestart}
          className="text-sm px-6 py-3 rounded-lg bg-blue-600 text-white hover:bg-blue-500 transition-colors"
        >
          Try Again
        </button>
        <button
          onClick={onDownloadPdf}
          disabled={downloading}
          className="text-sm px-6 py-3 rounded-lg bg-gray-700 text-white hover:bg-gray-600 transition-colors disabled:opacity-50"
        >
          {downloading ? "Downloading..." : "Download PDF"}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AnswerResult {
  readonly answer: string;
  readonly correct: boolean;
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function WorksheetPage() {
  const params = useParams();
  const router = useRouter();
  const artifactId = params.artifactId as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [worksheet, setWorksheet] = useState<WorksheetContent | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [answers, setAnswers] = useState<ReadonlyMap<number, AnswerResult>>(
    new Map()
  );
  const [submitted, setSubmitted] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!artifactId) return;
    let cancelled = false;

    async function fetchData() {
      try {
        const data = await getArtifact(artifactId);
        if (!cancelled) {
          setArtifact(data);
          setWorksheet(data.content_json as unknown as WorksheetContent);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          logger.error("worksheet_fetch_failed", { error: String(err) });
          setError("Failed to load worksheet.");
          setLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, [artifactId]);

  const problems: readonly WorksheetProblem[] = worksheet?.problems ?? [];
  const currentProblem: WorksheetProblem | undefined = problems[currentIndex];
  const totalProblems = problems.length;

  const handleSubmitAnswer = useCallback(() => {
    if (!currentProblem || !currentAnswer.trim()) return;

    const isCorrect =
      currentAnswer.trim().toLowerCase() ===
      currentProblem.answer.trim().toLowerCase();

    const newAnswers = new Map(answers);
    newAnswers.set(currentIndex, {
      answer: currentAnswer,
      correct: isCorrect,
    });
    setAnswers(newAnswers);
    setSubmitted(true);
    logger.debug("answer_submitted", {
      problem: currentIndex,
      correct: isCorrect,
    });
  }, [currentProblem, currentAnswer, currentIndex, answers]);

  const handleNext = useCallback(() => {
    if (currentIndex < totalProblems - 1) {
      setCurrentIndex(currentIndex + 1);
      setCurrentAnswer("");
      setSubmitted(false);
    } else {
      setCompleted(true);
    }
  }, [currentIndex, totalProblems]);

  const handleRestart = useCallback(() => {
    setCurrentIndex(0);
    setCurrentAnswer("");
    setAnswers(new Map());
    setSubmitted(false);
    setCompleted(false);
  }, []);

  const handleDownloadPdf = useCallback(async () => {
    if (!artifact) return;
    setDownloading(true);
    try {
      const blob = await downloadArtifactPdf(artifact.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${worksheet?.title ?? "worksheet"}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      logger.error("pdf_download_failed", { error: String(err) });
    } finally {
      setDownloading(false);
    }
  }, [artifact, worksheet?.title]);

  const correctCount = Array.from(answers.values()).filter(
    (r) => r.correct
  ).length;

  const currentResult = answers.get(currentIndex);

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
          onClick={() => router.push("/")}
          className="flex items-center gap-2.5 bg-transparent border-none cursor-pointer"
          aria-label="Go to home page"
        >
          <div
            className="flex items-center justify-center w-9 h-9 rounded-[10px] text-white text-base font-extrabold"
            style={{ background: "linear-gradient(135deg, #007AFF, #0056b3)" }}
          >
            N
          </div>
          <span className="text-white font-bold text-lg" style={{ letterSpacing: "-0.02em" }}>
            Nerdy AI Tutor
          </span>
        </button>
        {!loading && !error && (
          <span className="text-white/60 text-sm">
            {worksheet?.title ?? "Worksheet"}
          </span>
        )}
      </nav>

      {/* Content */}
      <main className="mx-auto px-6 py-10" style={{ maxWidth: 700 }}>
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-1.5 bg-transparent border-none cursor-pointer text-blue-400 text-sm hover:text-blue-300 mb-6"
          style={{ fontFamily: "inherit" }}
        >
          <span>&larr;</span> Back to Dashboard
        </button>
        {loading && (
          <div className="text-center py-20">
            <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-400 text-sm">Loading worksheet...</p>
          </div>
        )}

        {error && (
          <div className="text-center py-20">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {!loading && !error && worksheet && !completed && currentProblem && (
          <>
            <ProgressDots
              total={totalProblems}
              current={currentIndex}
              answers={answers}
            />

            <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-6">
              {/* Problem header */}
              <div className="flex items-center gap-3 mb-4">
                <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">
                  {currentIndex + 1} / {totalProblems}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded ${
                    currentProblem.difficulty === "easy"
                      ? "bg-green-900/40 text-green-400"
                      : currentProblem.difficulty === "medium"
                        ? "bg-amber-900/40 text-amber-400"
                        : "bg-red-900/40 text-red-400"
                  }`}
                >
                  {currentProblem.difficulty}
                </span>
              </div>

              {/* Question */}
              <p className="text-white text-base mb-6 leading-relaxed">
                {currentProblem.question}
              </p>
              {currentProblem.question_latex && (
                <div className="text-gray-300 text-sm font-mono bg-gray-900 rounded px-3 py-2 mb-6">
                  {currentProblem.question_latex}
                </div>
              )}

              {/* Answer input */}
              {currentProblem.type === "multiple_choice" &&
                currentProblem.options && (
                  <MultipleChoiceInput
                    options={currentProblem.options}
                    selected={currentAnswer}
                    onSelect={setCurrentAnswer}
                    disabled={submitted}
                    correctAnswer={currentProblem.answer}
                    submitted={submitted}
                  />
                )}
              {currentProblem.type === "short_answer" && (
                <ShortAnswerInput
                  value={currentAnswer}
                  onChange={setCurrentAnswer}
                  disabled={submitted}
                />
              )}
              {currentProblem.type === "show_work" && (
                <ShowWorkInput
                  value={currentAnswer}
                  onChange={setCurrentAnswer}
                  disabled={submitted}
                />
              )}

              {/* Feedback */}
              {submitted && currentResult && (
                <div
                  className={`mt-4 p-3 rounded-lg border ${
                    currentResult.correct
                      ? "bg-green-900/20 border-green-700 text-green-300"
                      : "bg-red-900/20 border-red-700 text-red-300"
                  }`}
                >
                  <p className="text-sm font-medium mb-1">
                    {currentResult.correct ? "Correct!" : "Incorrect"}
                  </p>
                  {!currentResult.correct && (
                    <p className="text-xs opacity-80">
                      Answer: {currentProblem.answer}
                    </p>
                  )}
                  <p className="text-xs opacity-70 mt-1">
                    {currentProblem.explanation}
                  </p>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 mt-6">
                {!submitted ? (
                  <button
                    onClick={handleSubmitAnswer}
                    disabled={!currentAnswer.trim()}
                    className="text-sm px-6 py-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Check Answer
                  </button>
                ) : (
                  <button
                    onClick={handleNext}
                    className="text-sm px-6 py-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-500 transition-colors"
                  >
                    {currentIndex < totalProblems - 1
                      ? "Next Problem"
                      : "See Results"}
                  </button>
                )}
              </div>
            </div>
          </>
        )}

        {!loading && !error && completed && (
          <ScoreSummary
            correct={correctCount}
            total={totalProblems}
            onRestart={handleRestart}
            onDownloadPdf={handleDownloadPdf}
            downloading={downloading}
          />
        )}
      </main>
    </div>
  );
}
