"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getSession, listFlashCards, updateFlashCardMastery, generateFlashCards } from "@/lib/api";
import { getUserId } from "@/lib/user";
import type { Session, FlashCard, FlashCardMastery } from "@/lib/types";
import { createLogger } from "@/lib/logger";

const logger = createLogger("SessionFlashCardsPage");

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

function masteryLabel(mastery: FlashCardMastery): string {
  switch (mastery) {
    case "new":
      return "New";
    case "learning":
      return "Learning";
    case "known":
      return "Known";
    default:
      return mastery;
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProgressBar({ cards }: { readonly cards: readonly FlashCard[] }) {
  const total = cards.length;
  if (total === 0) return null;

  const known = cards.filter((c) => c.mastery === "known").length;
  const learning = cards.filter((c) => c.mastery === "learning").length;
  const newCount = total - known - learning;

  return (
    <div className="mb-8">
      <div className="w-full h-3 bg-gray-700 rounded-full overflow-hidden flex">
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${(known / total) * 100}%`, background: "#22C55E" }}
        />
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${(learning / total) * 100}%`, background: "#F59E0B" }}
        />
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${(newCount / total) * 100}%`, background: "#EF4444" }}
        />
      </div>
      <div className="flex gap-4 mt-2 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500" /> {known} known
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-500" /> {learning} learning
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-500" /> {newCount} new
        </span>
      </div>
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
    <div className="w-full" style={{ maxWidth: 520, margin: "0 auto" }}>
      {/* Card */}
      <div
        role="button"
        tabIndex={0}
        aria-label={
          flipped
            ? "Flash card showing definition. Click to see term."
            : "Flash card showing term. Click to see definition."
        }
        onClick={onFlip}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onFlip();
          }
        }}
        className="relative w-full cursor-pointer rounded-2xl border transition-all duration-300"
        style={{
          minHeight: 220,
          background: flipped
            ? "linear-gradient(135deg, rgba(0,122,255,0.08), rgba(0,86,179,0.04))"
            : "rgba(255,255,255,0.04)",
          borderColor: flipped
            ? "rgba(0,122,255,0.3)"
            : "rgba(255,255,255,0.08)",
        }}
      >
        <div
          className="flex flex-col items-center justify-center p-8 text-center h-full"
          style={{ minHeight: 220 }}
        >
          {!flipped ? (
            <>
              <span
                className="text-xs uppercase tracking-wider mb-3 font-semibold"
                style={{ color: "#6a7f99" }}
              >
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
              <span
                className="text-xs uppercase tracking-wider mb-3 font-semibold"
                style={{ color: "#007AFF" }}
              >
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
        <div className="absolute top-3 right-3 flex items-center gap-1.5">
          <span
            className="w-2.5 h-2.5 rounded-full inline-block"
            style={{ background: masteryColor(card.mastery) }}
          />
          <span className="text-xs" style={{ color: "#6a7f99" }}>
            {masteryLabel(card.mastery)}
          </span>
        </div>
      </div>

      {/* Mastery buttons — shown when flipped */}
      {flipped && (
        <div className="flex gap-3 mt-4 justify-center">
          <button
            onClick={() => onMastery("new")}
            disabled={updating}
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

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function SessionFlashCardsPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId =
    typeof params.sessionId === "string" ? params.sessionId : null;

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [cards, setCards] = useState<readonly FlashCard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    const sid = sessionId;
    const userId = getUserId();
    let cancelled = false;

    async function fetchData() {
      try {
        const [sessionData, allCards] = await Promise.all([
          getSession(sid),
          userId
            ? listFlashCards(userId).catch(() => [] as FlashCard[])
            : Promise.resolve([] as FlashCard[]),
        ]);
        if (cancelled) return;

        setSession(sessionData);
        const sessionCards = allCards.filter((c) => c.source_session_id === sid);

        if (sessionCards.length === 0 && userId) {
          // Auto-generate flash cards for this session
          setLoading(false);
          setGenerating(true);
          try {
            const generated = await generateFlashCards(sid, userId);
            if (!cancelled) {
              setCards(generated);
              setGenerating(false);
            }
          } catch (err) {
            if (!cancelled) {
              logger.error("flash_cards_generate_failed", { error: String(err) });
              setGenerating(false);
            }
          }
        } else {
          setCards(sessionCards);
          setLoading(false);
        }
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
  }, [sessionId]);

  const currentCard = cards.length > 0 ? cards[currentIndex] : null;

  const handleFlip = useCallback(() => {
    setFlipped((prev) => !prev);
  }, []);

  const handlePrev = useCallback(() => {
    setFlipped(false);
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : cards.length - 1));
  }, [cards.length]);

  const handleNext = useCallback(() => {
    setFlipped(false);
    setCurrentIndex((prev) => (prev < cards.length - 1 ? prev + 1 : 0));
  }, [cards.length]);

  const handleMastery = useCallback(
    async (mastery: FlashCardMastery) => {
      const card = cards[currentIndex];
      if (!card) return;

      setUpdating(true);
      try {
        await updateFlashCardMastery(card.id, mastery);
        setCards((prev) =>
          prev.map((c) => (c.id === card.id ? { ...c, mastery } : c)),
        );
        // Advance to next card
        setFlipped(false);
        if (currentIndex < cards.length - 1) {
          setCurrentIndex((prev) => prev + 1);
        } else {
          setCurrentIndex(0);
        }
      } catch (err) {
        logger.error("mastery_update_failed", { error: String(err) });
      } finally {
        setUpdating(false);
      }
    },
    [cards, currentIndex],
  );

  if (!sessionId) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: "#0a1d37" }}
      >
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
          onClick={() => router.push(`/reviews/${sessionId}`)}
          className="flex items-center gap-2 bg-transparent border-none cursor-pointer text-blue-400 text-sm hover:text-blue-300"
          style={{ fontFamily: "inherit" }}
        >
          <span>&larr;</span> Back to Review
        </button>
        {session && (
          <span className="text-white/60 text-sm">
            {session.subject.replace(/_/g, " ")} &middot; Grade {session.grade}
          </span>
        )}
      </nav>

      {/* Content */}
      <main className="mx-auto px-6 py-10" style={{ maxWidth: 640 }}>
        {loading && (
          <div className="text-center py-20">
            <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-400 text-sm">Loading flash cards...</p>
          </div>
        )}

        {generating && (
          <div className="text-center py-20">
            <div className="w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-400 text-sm">Generating flash cards from your session...</p>
          </div>
        )}

        {!loading && !generating && (
          <>
            <h1 className="text-2xl font-bold text-white mb-2 text-center">
              Flash Cards
            </h1>
            <p className="text-center text-sm mb-8" style={{ color: "#6a7f99" }}>
              {cards.length} card{cards.length !== 1 ? "s" : ""} from this
              session
            </p>

            {cards.length === 0 ? (
              <div className="text-center py-16">
                <p className="text-gray-400 text-sm mb-4">
                  Could not generate flash cards for this session.
                </p>
                <button
                  onClick={() => router.push(`/reviews/${sessionId}`)}
                  className="text-blue-400 text-sm hover:text-blue-300 bg-transparent border-none cursor-pointer"
                  style={{ fontFamily: "inherit" }}
                >
                  Back to review
                </button>
              </div>
            ) : (
              <>
                <ProgressBar cards={cards} />

                {/* Navigation */}
                <div className="flex items-center justify-between mb-6">
                  <button
                    onClick={handlePrev}
                    disabled={cards.length <= 1}
                    className="text-sm font-medium bg-transparent border-none cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                    style={{ color: "#007AFF", fontFamily: "inherit" }}
                  >
                    &larr; Previous
                  </button>
                  <span className="text-sm" style={{ color: "#6a7f99" }}>
                    {currentIndex + 1} / {cards.length}
                  </span>
                  <button
                    onClick={handleNext}
                    disabled={cards.length <= 1}
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
      </main>
    </div>
  );
}
