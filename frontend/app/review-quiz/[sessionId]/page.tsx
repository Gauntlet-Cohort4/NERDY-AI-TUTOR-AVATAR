"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { startReviewQuiz } from "@/lib/api";
import type { ReviewQuizContent, ReviewQuestion } from "@/lib/types";
import { createLogger } from "@/lib/logger";

const logger = createLogger("ReviewQuizPage");

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface QuizResult {
  readonly id: string;
  readonly correct: boolean;
  readonly correctAnswer: string;
  readonly userAnswer: string;
  readonly question: string;
  readonly topic: string;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LoadingState({ text }: { readonly text: string }) {
  return (
    <div className="text-center py-20">
      <div className="w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
      <p className="text-gray-400 text-sm">{text}</p>
    </div>
  );
}

function QuestionCard({
  question,
  index,
  total,
  answer,
  onAnswer,
  onSubmit,
  submitted,
  isCorrect,
}: {
  readonly question: ReviewQuestion;
  readonly index: number;
  readonly total: number;
  readonly answer: string;
  readonly onAnswer: (val: string) => void;
  readonly onSubmit: () => void;
  readonly submitted: boolean;
  readonly isCorrect: boolean | null;
}) {
  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">
          {index + 1} / {total}
        </span>
        <span className="text-xs text-gray-500">{question.topic}</span>
        <span
          className={`text-xs px-2 py-0.5 rounded ml-auto ${
            question.difficulty === "easy"
              ? "bg-green-900/40 text-green-400"
              : question.difficulty === "medium"
                ? "bg-amber-900/40 text-amber-400"
                : "bg-red-900/40 text-red-400"
          }`}
        >
          {question.difficulty}
        </span>
      </div>

      {/* Question */}
      <p className="text-white text-base mb-6 leading-relaxed">
        {question.question}
      </p>
      {question.question_latex && (
        <div className="text-gray-300 text-sm font-mono bg-gray-900 rounded px-3 py-2 mb-6">
          {question.question_latex}
        </div>
      )}

      {/* Answer input */}
      {question.type === "multiple_choice" && question.options ? (
        <div className="space-y-2">
          {question.options.map((option, i) => {
            const letter = String.fromCharCode(65 + i);
            const isSelected = answer === letter;
            const showCorrect =
              submitted && letter === question.correct_answer;
            const showWrong =
              submitted && isSelected && letter !== question.correct_answer;

            let borderClass = "border-gray-600";
            if (showCorrect) borderClass = "border-green-400";
            else if (showWrong) borderClass = "border-red-400";
            else if (isSelected && !submitted) borderClass = "border-blue-400";

            return (
              <button
                key={i}
                onClick={() => onAnswer(letter)}
                disabled={submitted}
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
      ) : (
        <input
          type="text"
          value={answer}
          onChange={(e) => onAnswer(e.target.value)}
          disabled={submitted}
          placeholder="Type your answer..."
          className="w-full px-4 py-3 rounded-lg border border-gray-600 bg-gray-800/60 text-sm text-white placeholder-gray-500 focus:border-blue-400 focus:outline-none disabled:cursor-not-allowed"
        />
      )}

      {/* Feedback */}
      {submitted && isCorrect !== null && (
        <div
          className={`mt-4 p-3 rounded-lg border ${
            isCorrect
              ? "bg-green-900/20 border-green-700 text-green-300"
              : "bg-red-900/20 border-red-700 text-red-300"
          }`}
        >
          <p className="text-sm font-medium">
            {isCorrect ? "Correct!" : "Not quite."}
          </p>
          {!isCorrect && (
            <p className="text-xs opacity-80 mt-1">
              Correct answer: {question.correct_answer}
            </p>
          )}
          {question.hint && !isCorrect && (
            <p className="text-xs opacity-70 mt-1">Hint: {question.hint}</p>
          )}
        </div>
      )}

      {/* Submit / Next */}
      {!submitted && (
        <button
          onClick={onSubmit}
          disabled={!answer.trim()}
          className="mt-6 text-sm px-6 py-2.5 rounded-lg bg-purple-600 text-white hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Check
        </button>
      )}
    </div>
  );
}

function ResultsPage({
  results,
  onRetry,
  onBack,
}: {
  readonly results: readonly QuizResult[];
  readonly onRetry: () => void;
  readonly onBack: () => void;
}) {
  const gotIt = results.filter((r) => r.correct);
  const reviewThese = results.filter((r) => !r.correct);

  return (
    <div>
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-white mb-2">Quiz Results</h2>
        <p className="text-4xl font-extrabold text-purple-400 mb-1">
          {gotIt.length}/{results.length}
        </p>
        <p className="text-gray-400 text-sm">
          {Math.round((gotIt.length / Math.max(results.length, 1)) * 100)}%
          correct
        </p>
      </div>

      {/* Got It */}
      {gotIt.length > 0 && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-green-400 uppercase tracking-wider mb-3">
            Got It ({gotIt.length})
          </h3>
          <div className="space-y-2">
            {gotIt.map((r) => (
              <div
                key={r.id}
                className="bg-green-900/10 border border-green-800/30 rounded-lg px-4 py-3"
              >
                <p className="text-sm text-gray-300">{r.question}</p>
                <p className="text-xs text-gray-500 mt-1">{r.topic}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Review These */}
      {reviewThese.length > 0 && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider mb-3">
            Review These ({reviewThese.length})
          </h3>
          <div className="space-y-2">
            {reviewThese.map((r) => (
              <div
                key={r.id}
                className="bg-red-900/10 border border-red-800/30 rounded-lg px-4 py-3"
              >
                <p className="text-sm text-gray-300">{r.question}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Your answer: {r.userAnswer} | Correct: {r.correctAnswer}
                </p>
                <p className="text-xs text-gray-500">{r.topic}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="flex gap-4 justify-center">
        <button
          onClick={onRetry}
          className="text-sm px-6 py-3 rounded-lg bg-purple-600 text-white hover:bg-purple-500 transition-colors"
        >
          Retry Quiz
        </button>
        <button
          onClick={onBack}
          className="text-sm px-6 py-3 rounded-lg bg-gray-700 text-white hover:bg-gray-600 transition-colors"
        >
          Back to Reviews
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ReviewQuizPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = typeof params.sessionId === "string" ? params.sessionId : null;

  const [phase, setPhase] = useState<
    "loading" | "quiz" | "results" | "error"
  >("loading");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [questions, setQuestions] = useState<readonly ReviewQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState<
    ReadonlyMap<number, string>
  >(new Map());
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [questionResults, setQuestionResults] = useState<
    ReadonlyMap<number, boolean>
  >(new Map());
  const [finalResults, setFinalResults] = useState<readonly QuizResult[]>([]);

  const cleanupRef = useRef<(() => void) | null>(null);

  const startQuiz = useCallback(() => {
    if (!sessionId) return;
    setPhase("loading");
    setQuestions([]);
    setCurrentIndex(0);
    setUserAnswers(new Map());
    setCurrentAnswer("");
    setSubmitted(false);
    setQuestionResults(new Map());
    setFinalResults([]);

    const cleanup = startReviewQuiz(sessionId, {
      onDone: (event) => {
        try {
          const content: ReviewQuizContent = JSON.parse(event.full_text);
          if (content.questions.length === 0) {
            setErrorMsg("No questions were generated for this session.");
            setPhase("error");
            return;
          }
          setQuestions(content.questions);
          setPhase("quiz");
          logger.info("quiz_loaded", {
            questionCount: content.questions.length,
          });
        } catch (err) {
          logger.error("quiz_parse_failed", { error: String(err) });
          setErrorMsg("Failed to parse quiz data.");
          setPhase("error");
        }
      },
      onError: () => {
        logger.error("quiz_sse_error", { sessionId });
        setErrorMsg("Failed to generate quiz. Please try again.");
        setPhase("error");
      },
    });

    cleanupRef.current = cleanup;
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    startQuiz();
    return () => {
      cleanupRef.current?.();
    };
  }, [sessionId, startQuiz]);

  const currentQuestion: ReviewQuestion | undefined = questions[currentIndex];

  const handleSubmitAnswer = useCallback(() => {
    if (!currentQuestion || !currentAnswer.trim()) return;

    const isCorrect =
      currentAnswer.trim().toLowerCase() ===
        currentQuestion.correct_answer.trim().toLowerCase() ||
      currentQuestion.accept_also.some(
        (alt) =>
          alt.trim().toLowerCase() === currentAnswer.trim().toLowerCase()
      );

    const newAnswers = new Map(userAnswers);
    newAnswers.set(currentIndex, currentAnswer);
    setUserAnswers(newAnswers);

    const newResults = new Map(questionResults);
    newResults.set(currentIndex, isCorrect);
    setQuestionResults(newResults);

    setSubmitted(true);
    logger.debug("quiz_answer_submitted", {
      question: currentIndex,
      correct: isCorrect,
    });
  }, [currentQuestion, currentAnswer, currentIndex, userAnswers, questionResults]);

  const handleNext = useCallback(() => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setCurrentAnswer("");
      setSubmitted(false);
    } else {
      // Build final results
      const results: QuizResult[] = questions.map((q, i) => ({
        id: q.id,
        correct: questionResults.get(i) ?? false,
        correctAnswer: q.correct_answer,
        userAnswer: userAnswers.get(i) ?? "",
        question: q.question,
        topic: q.topic,
      }));
      setFinalResults(results);
      setPhase("results");
      logger.info("quiz_completed", {
        score: results.filter((r) => r.correct).length,
        total: results.length,
      });
    }
  }, [currentIndex, questions, questionResults, userAnswers]);

  const handleRetry = useCallback(() => {
    cleanupRef.current?.();
    cleanupRef.current = null;
    startQuiz();
  }, [startQuiz]);

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
        <span className="text-white/60 text-sm">Review Quiz</span>
      </nav>

      {/* Content */}
      <main className="mx-auto px-6 py-10" style={{ maxWidth: 700 }}>
        {phase === "loading" && (
          <LoadingState text="Generating review quiz..." />
        )}

        {phase === "error" && (
          <div className="text-center py-20">
            <p className="text-red-400 text-sm mb-4">{errorMsg}</p>
            <button
              onClick={handleRetry}
              className="text-blue-400 text-sm hover:text-blue-300"
            >
              Try Again
            </button>
          </div>
        )}

        {phase === "quiz" && currentQuestion && (
          <>
            {/* Progress dots */}
            <div className="flex gap-1.5 justify-center mb-6 flex-wrap">
              {questions.map((_, i) => {
                const result = questionResults.get(i);
                const isCurrent = i === currentIndex;
                let bg = "bg-gray-600";
                if (result === true) bg = "bg-green-400";
                else if (result === false) bg = "bg-red-400";
                else if (isCurrent) bg = "bg-purple-400";

                return (
                  <span
                    key={i}
                    className={`w-3 h-3 rounded-full ${bg} ${isCurrent ? "ring-2 ring-purple-300" : ""}`}
                  />
                );
              })}
            </div>

            <QuestionCard
              question={currentQuestion}
              index={currentIndex}
              total={questions.length}
              answer={currentAnswer}
              onAnswer={setCurrentAnswer}
              onSubmit={handleSubmitAnswer}
              submitted={submitted}
              isCorrect={questionResults.get(currentIndex) ?? null}
            />

            {submitted && (
              <div className="text-center mt-4">
                <button
                  onClick={handleNext}
                  className="text-sm px-6 py-2.5 rounded-lg bg-purple-600 text-white hover:bg-purple-500 transition-colors"
                >
                  {currentIndex < questions.length - 1
                    ? "Next Question"
                    : "See Results"}
                </button>
              </div>
            )}
          </>
        )}

        {phase === "results" && (
          <ResultsPage
            results={finalResults}
            onRetry={handleRetry}
            onBack={() => router.push("/reviews")}
          />
        )}
      </main>
    </div>
  );
}
