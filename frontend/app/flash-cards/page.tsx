"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { createLogger } from "@/lib/logger";
import { getUserId } from "@/lib/user";
import { listFlashCards, updateFlashCardMastery, getFlashCardStats } from "@/lib/api";
import ToastNotification from "@/components/ToastNotification";
import type { Toast } from "@/components/ToastNotification";
import type { FlashCard, FlashCardMastery, FlashCardStats, Subject } from "@/lib/types";

const logger = createLogger("FlashCardsPage");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function masteryColor(mastery: FlashCardMastery): string {
  switch (mastery) {
    case "new":
      return "#EF4444";
    case "learning":
      return "#F59E0B";
    case "known":
      return "#22C55E";
    default:
      return "#6a7f99";
  }
}

function subjectLabel(subject: string): string {
  return subject.replace(/_/g, " ");
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatsBar({
  stats,
  subject,
}: {
  readonly stats: FlashCardStats;
  readonly subject: string;
}) {
  const { total } = stats;
  if (total === 0) return null;

  const knownPct = Math.round((stats.known / total) * 100);
  const learningPct = Math.round((stats.learning / total) * 100);
  const newPct = Math.max(0, 100 - knownPct - learningPct);

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-white capitalize">
          {subjectLabel(subject)}
        </span>
        <span className="text-xs" style={{ color: "#6a7f99" }}>
          {total} card{total !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="w-full h-3 bg-gray-700 rounded-full overflow-hidden flex" role="progressbar" aria-label={`${subject} progress`}>
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${knownPct}%`, background: "#22C55E" }}
        />
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${learningPct}%`, background: "#F59E0B" }}
        />
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${newPct}%`, background: "#EF4444" }}
        />
      </div>
      <div className="flex gap-4 mt-2 text-xs" style={{ color: "#6a7f99" }}>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500" /> {stats.known} known
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-500" /> {stats.learning} learning
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-500" /> {stats.new} new
        </span>
      </div>
    </div>
  );
}

function SubjectTabs({
  subjects,
  activeSubject,
  onSelect,
}: {
  readonly subjects: readonly string[];
  readonly activeSubject: string | null;
  readonly onSelect: (subject: string | null) => void;
}) {
  return (
    <div className="flex gap-2 flex-wrap mb-6" role="tablist" aria-label="Subject filter">
      <button
        role="tab"
        aria-selected={activeSubject === null}
        onClick={() => onSelect(null)}
        className="px-4 py-2 rounded-lg text-sm font-medium border-none cursor-pointer transition-all duration-200"
        style={{
          background: activeSubject === null ? "#007AFF" : "rgba(255,255,255,0.06)",
          color: activeSubject === null ? "#fff" : "#6a7f99",
          fontFamily: "inherit",
        }}
      >
        All
      </button>
      {subjects.map((subject) => (
        <button
          key={subject}
          role="tab"
          aria-selected={activeSubject === subject}
          onClick={() => onSelect(subject)}
          className="px-4 py-2 rounded-lg text-sm font-medium border-none cursor-pointer capitalize transition-all duration-200"
          style={{
            background: activeSubject === subject ? "#007AFF" : "rgba(255,255,255,0.06)",
            color: activeSubject === subject ? "#fff" : "#6a7f99",
            fontFamily: "inherit",
          }}
        >
          {subjectLabel(subject)}
        </button>
      ))}
    </div>
  );
}

function FlashCardView({
  card,
  flipped,
  onFlip,
  onMastery,
  updating,
}: {
  readonly card: FlashCard;
  readonly flipped: boolean;
  readonly onFlip: () => void;
  readonly onMastery: (mastery: FlashCardMastery) => void;
  readonly updating: boolean;
}) {
  return (
    <div className="w-full" style={{ maxWidth: 480, margin: "0 auto" }}>
      {/* Card */}
      <div
        role="button"
        tabIndex={0}
        aria-label={flipped ? "Flash card showing definition. Click to see term." : "Flash card showing term. Click to see definition."}
        onClick={onFlip}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onFlip();
          }
        }}
        className="relative w-full cursor-pointer rounded-2xl border transition-all duration-500"
        style={{
          minHeight: 240,
          background: flipped
            ? "linear-gradient(135deg, rgba(0,122,255,0.08), rgba(0,86,179,0.04))"
            : "rgba(255,255,255,0.04)",
          borderColor: flipped ? "rgba(0,122,255,0.3)" : "rgba(255,255,255,0.08)",
          transformStyle: "preserve-3d",
          perspective: 1000,
        }}
      >
        <div
          className="flex flex-col items-center justify-center p-8 text-center h-full"
          style={{ minHeight: 240 }}
        >
          {!flipped ? (
            <>
              <span className="text-xs uppercase tracking-wider mb-3 font-semibold" style={{ color: "#6a7f99" }}>
                Term
              </span>
              <p className="text-white text-xl font-bold leading-relaxed">
                {card.term}
              </p>
              <span className="text-xs mt-4" style={{ color: "#506480" }}>
                Click to reveal definition
              </span>
            </>
          ) : (
            <>
              <span className="text-xs uppercase tracking-wider mb-3 font-semibold" style={{ color: "#007AFF" }}>
                Definition
              </span>
              <p className="text-white text-base leading-relaxed mb-3">
                {card.definition}
              </p>
              {card.example && (
                <p className="text-sm italic" style={{ color: "#6a7f99" }}>
                  Example: {card.example}
                </p>
              )}
            </>
          )}
        </div>

        {/* Mastery indicator */}
        <div className="absolute top-3 right-3">
          <span
            className="w-3 h-3 rounded-full inline-block"
            style={{ background: masteryColor(card.mastery) }}
            title={`Current mastery: ${card.mastery}`}
          />
        </div>
      </div>

      {/* Mastery buttons */}
      {flipped && (
        <div className="flex gap-3 mt-4 justify-center" style={{ animation: "fade-slide-up 0.3s ease both" }}>
          <button
            onClick={() => onMastery("new")}
            disabled={updating}
            aria-label="Mark as still learning"
            className="flex-1 py-3 rounded-xl text-sm font-semibold border-none cursor-pointer transition-all duration-200 disabled:opacity-40"
            style={{
              background: "rgba(239,68,68,0.15)",
              color: "#EF4444",
              fontFamily: "inherit",
            }}
          >
            Still Learning
          </button>
          <button
            onClick={() => onMastery("learning")}
            disabled={updating}
            aria-label="Mark as getting there"
            className="flex-1 py-3 rounded-xl text-sm font-semibold border-none cursor-pointer transition-all duration-200 disabled:opacity-40"
            style={{
              background: "rgba(245,158,11,0.15)",
              color: "#F59E0B",
              fontFamily: "inherit",
            }}
          >
            Getting There
          </button>
          <button
            onClick={() => onMastery("known")}
            disabled={updating}
            aria-label="Mark as got it"
            className="flex-1 py-3 rounded-xl text-sm font-semibold border-none cursor-pointer transition-all duration-200 disabled:opacity-40"
            style={{
              background: "rgba(34,197,94,0.15)",
              color: "#22C55E",
              fontFamily: "inherit",
            }}
          >
            Got It!
          </button>
        </div>
      )}
    </div>
  );
}

function EmptyState({ hasFilter }: { readonly hasFilter: boolean }) {
  return (
    <div className="text-center py-16">
      <svg
        aria-hidden="true"
        className="mx-auto mb-4"
        width="48"
        height="48"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#6a7f99"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="2" y="6" width="20" height="12" rx="2" />
        <path d="M12 12h.01" />
      </svg>
      <h3 className="text-white text-lg font-semibold mb-2">
        {hasFilter ? "No cards for this subject" : "No flash cards yet"}
      </h3>
      <p className="text-sm" style={{ color: "#6a7f99" }}>
        {hasFilter
          ? "Try selecting a different subject or view all cards."
          : "Complete a tutoring session to generate flash cards from your lessons."}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function FlashCardsPage() {
  const router = useRouter();
  const [cards, setCards] = useState<readonly FlashCard[]>([]);
  const [stats, setStats] = useState<Readonly<Record<string, FlashCardStats>>>({});
  const [activeSubject, setActiveSubject] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [toasts, setToasts] = useState<readonly Toast[]>([]);

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

  // Load cards and stats
  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchData() {
      try {
        const [cardsResult, statsResult] = await Promise.allSettled([
          listFlashCards(userId!),
          getFlashCardStats(userId!),
        ]);

        if (cancelled) return;

        if (cardsResult.status === "fulfilled" && Array.isArray(cardsResult.value)) {
          setCards(cardsResult.value);
        } else if (cardsResult.status === "rejected") {
          logger.warn("cards_fetch_failed", { error: String(cardsResult.reason) });
        }

        if (statsResult.status === "fulfilled" && typeof statsResult.value === "object") {
          setStats(statsResult.value);
        } else if (statsResult.status === "rejected") {
          logger.warn("stats_fetch_failed", { error: String(statsResult.reason) });
        }

        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          logger.error("flash_cards_fetch_failed", { error: String(err) });
          setLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const subjects = useMemo(() => {
    const uniqueSubjects = new Set(cards.map((c) => c.subject));
    return Array.from(uniqueSubjects).sort();
  }, [cards]);

  const filteredCards = useMemo(() => {
    if (!activeSubject) return cards;
    return cards.filter((c) => c.subject === activeSubject);
  }, [cards, activeSubject]);

  const currentCard = filteredCards.length > 0 ? filteredCards[currentIndex] : null;

  // Reset index when filter changes
  useEffect(() => {
    setCurrentIndex(0);
    setFlipped(false);
  }, [activeSubject]);

  const handleFlip = useCallback(() => {
    setFlipped((prev) => !prev);
  }, []);

  const handleMastery = useCallback(
    async (mastery: FlashCardMastery) => {
      const card = filteredCards[currentIndex];
      if (!card) return;
      const cardId = card.id;
      const cardSubject = card.subject;
      const cardOldMastery = card.mastery;
      const idx = currentIndex;

      setUpdating(true);
      try {
        await updateFlashCardMastery(cardId, mastery);

        // Update local state immutably
        setCards((prev) =>
          prev.map((c) => (c.id === cardId ? { ...c, mastery } : c)),
        );

        // Update stats immutably
        setStats((prev) => {
          const subjectStats = prev[cardSubject];
          if (!subjectStats) return prev;

          return {
            ...prev,
            [cardSubject]: {
              ...subjectStats,
              [cardOldMastery]: Math.max(0, subjectStats[cardOldMastery] - 1),
              [mastery]: subjectStats[mastery] + 1,
            },
          };
        });

        // Move to next card
        setFlipped(false);
        if (idx < filteredCards.length - 1) {
          setCurrentIndex((prev) => prev + 1);
        } else {
          setCurrentIndex(0);
          addToast("You reviewed all cards in this set!", "success");
        }

        logger.debug("mastery_updated", {
          cardId,
          mastery,
        });
      } catch (err) {
        logger.error("mastery_update_failed", { error: String(err) });
        addToast("Failed to update mastery. Please try again.", "error");
      } finally {
        setUpdating(false);
      }
    },
    [filteredCards, currentIndex, addToast],
  );

  const handleSubjectSelect = useCallback((subject: string | null) => {
    setActiveSubject(subject as Subject | null);
  }, []);

  const handlePrev = useCallback(() => {
    setFlipped(false);
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : filteredCards.length - 1));
  }, [filteredCards.length]);

  const handleNext = useCallback(() => {
    setFlipped(false);
    setCurrentIndex((prev) => (prev < filteredCards.length - 1 ? prev + 1 : 0));
  }, [filteredCards.length]);

  if (!userId) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0a1d37" }}>
        <div className="text-center max-w-md px-6">
          <h2 className="text-white text-xl font-bold mb-2">Session Required</h2>
          <p className="text-sm mb-6" style={{ color: "#6a7f99" }}>
            Start a tutoring session first to generate flash cards.
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
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/upload")}
            className="text-white/70 text-sm font-medium px-4 py-2 rounded-lg hover:text-white hover:bg-white/5 transition-colors bg-transparent border-none cursor-pointer"
            style={{ fontFamily: "inherit" }}
          >
            Upload Worksheet
          </button>
        </div>
      </nav>

      {/* Content */}
      <div className="mx-auto px-6 py-10" style={{ maxWidth: 720 }}>
        <h1 className="text-white text-2xl font-bold mb-2 text-center">
          Flash Cards
        </h1>
        <p className="text-center text-sm mb-8" style={{ color: "#6a7f99" }}>
          Review key concepts from your tutoring sessions.
        </p>

        {loading && (
          <div className="flex items-center justify-center py-16">
            <div
              className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: "#007AFF", borderTopColor: "transparent" }}
            />
            <span className="ml-3 text-sm" style={{ color: "#6a7f99" }}>
              Loading flash cards...
            </span>
          </div>
        )}

        {!loading && (
          <>
            {/* Stats */}
            {Object.keys(stats).length > 0 && (
              <div
                className="rounded-2xl border p-6 mb-8"
                style={{
                  background: "rgba(255,255,255,0.03)",
                  borderColor: "rgba(255,255,255,0.08)",
                }}
              >
                <h2 className="text-white text-sm font-semibold uppercase tracking-wider mb-4">
                  Progress
                </h2>
                {Object.entries(stats).map(([subject, stat]) => (
                  <StatsBar key={subject} stats={stat} subject={subject} />
                ))}
              </div>
            )}

            {/* Subject tabs */}
            {subjects.length > 1 && (
              <SubjectTabs
                subjects={subjects}
                activeSubject={activeSubject}
                onSelect={handleSubjectSelect}
              />
            )}

            {/* Card display */}
            {filteredCards.length === 0 ? (
              <EmptyState hasFilter={activeSubject !== null} />
            ) : (
              <>
                {/* Navigation */}
                <div className="flex items-center justify-between mb-4">
                  <button
                    onClick={handlePrev}
                    disabled={filteredCards.length <= 1}
                    aria-label="Previous card"
                    className="text-sm font-medium bg-transparent border-none cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                    style={{ color: "#007AFF", fontFamily: "inherit" }}
                  >
                    &larr; Previous
                  </button>
                  <span className="text-sm" style={{ color: "#6a7f99" }}>
                    {currentIndex + 1} / {filteredCards.length}
                  </span>
                  <button
                    onClick={handleNext}
                    disabled={filteredCards.length <= 1}
                    aria-label="Next card"
                    className="text-sm font-medium bg-transparent border-none cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                    style={{ color: "#007AFF", fontFamily: "inherit" }}
                  >
                    Next &rarr;
                  </button>
                </div>

                {currentCard && (
                  <FlashCardView
                    card={currentCard}
                    flipped={flipped}
                    onFlip={handleFlip}
                    onMastery={handleMastery}
                    updating={updating}
                  />
                )}
              </>
            )}
          </>
        )}
      </div>

      <ToastNotification toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
