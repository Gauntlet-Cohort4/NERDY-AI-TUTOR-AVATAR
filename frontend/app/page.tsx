"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { createLogger } from "@/lib/logger";
import { getUserId } from "@/lib/user";
import { listSessions, getFlashCardStats } from "@/lib/api";
import ToastNotification from "@/components/ToastNotification";
import type { Toast } from "@/components/ToastNotification";
import type { Subject, Session, FlashCardStats } from "@/lib/types";

const logger = createLogger("LandingPage");

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

interface Grade {
  readonly id: string;
  readonly label: string;
  readonly number: string;
}

interface SubjectConfig {
  readonly name: string;
  readonly subject: Subject;
  readonly topic: string;
  readonly icon: "leaf" | "calc" | "atom" | "globe" | "flask" | "cell" | "book" | "dna";
  readonly color: string;
  readonly bg: string;
}

const MIDDLE_SCHOOL: readonly Grade[] = [
  { id: "grade6", label: "Grade 6", number: "6" },
  { id: "grade7", label: "Grade 7", number: "7" },
  { id: "grade8", label: "Grade 8", number: "8" },
];

const HIGH_SCHOOL: readonly Grade[] = [
  { id: "grade9", label: "Grade 9", number: "9" },
  { id: "grade10", label: "Grade 10", number: "10" },
  { id: "grade11", label: "Grade 11", number: "11" },
  { id: "grade12", label: "Grade 12", number: "12" },
];

const ALL_GRADES: readonly Grade[] = [...MIDDLE_SCHOOL, ...HIGH_SCHOOL];

// Grade-specific subject maps (demo-ready)
const GRADE6_SUBJECTS: readonly SubjectConfig[] = [
  { name: "Fractions", subject: "math", topic: "Numerators, Denominators & More", icon: "calc", color: "#6F42C1", bg: "rgba(111,66,193,0.08)" },
];

const GRADE7_SUBJECTS: readonly SubjectConfig[] = [
  { name: "Basic Biology", subject: "biology", topic: "Plants & Photosynthesis", icon: "leaf", color: "#28A745", bg: "rgba(40,167,69,0.08)" },
];

const GRADE8_SUBJECTS: readonly SubjectConfig[] = [
  { name: "Intro Algebra", subject: "intro_algebra", topic: "Variables, Equations & Graphs", icon: "calc", color: "#6F42C1", bg: "rgba(111,66,193,0.08)" },
];

const HIGH_SCHOOL_LOWER_SUBJECTS: readonly SubjectConfig[] = [
  { name: "Algebra II", subject: "algebra_ii", topic: "Quadratics & Polynomials", icon: "calc", color: "#6F42C1", bg: "rgba(111,66,193,0.08)" },
  { name: "Chemistry", subject: "chemistry", topic: "Elements & Reactions", icon: "flask", color: "#FD7E14", bg: "rgba(253,126,20,0.08)" },
  { name: "Cell Biology", subject: "cell_biology", topic: "Cells & Organelles", icon: "cell", color: "#28A745", bg: "rgba(40,167,69,0.08)" },
  { name: "World History", subject: "world_history", topic: "Civilizations & Empires", icon: "book", color: "#DC3545", bg: "rgba(220,53,69,0.08)" },
];

const HIGH_SCHOOL_UPPER_SUBJECTS: readonly SubjectConfig[] = [
  { name: "Calculus", subject: "calculus", topic: "Derivatives & Integrals", icon: "calc", color: "#6F42C1", bg: "rgba(111,66,193,0.08)" },
  { name: "Physics", subject: "physics", topic: "Classical Mechanics", icon: "atom", color: "#FD7E14", bg: "rgba(253,126,20,0.08)" },
  { name: "AP Biology", subject: "ap_biology", topic: "Gene Expression & Evolution", icon: "dna", color: "#28A745", bg: "rgba(40,167,69,0.08)" },
];

const FEATURES = [
  { icon: "\uD83C\uDF99", label: "Microphone", title: "Voice In, Voice Out", desc: "Speak naturally, get instant audio responses" },
  { icon: "\uD83E\uDDE0", label: "Brain", title: "AI Video Avatar", desc: "A real-time tutor that explains visually" },
  { icon: "\uD83D\uDCCA", label: "Chart", title: "Step-by-Step", desc: "Every solution broken down clearly" },
] as const;

// ---------------------------------------------------------------------------
// SVG Icons
// ---------------------------------------------------------------------------

function LeafIcon({ color }: { color: string }) {
  return (
    <svg aria-hidden="true" focusable="false" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 8C8 10 5.9 16.17 3.82 21.34L5.71 22l1.41-3.53C10 16.5 13 14 17 8z" />
      <path d="M12.5 6.5C12.5 6.5 15 3 20 2c0 5-3 7.5-3 7.5" />
    </svg>
  );
}

function CalcIcon({ color }: { color: string }) {
  return (
    <svg aria-hidden="true" focusable="false" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 2h16a2 2 0 012 2v16a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2z" />
      <line x1="8" y1="6" x2="16" y2="6" />
      <line x1="12" y1="10" x2="12" y2="18" />
      <line x1="8" y1="14" x2="16" y2="14" />
    </svg>
  );
}

function AtomIcon({ color }: { color: string }) {
  return (
    <svg aria-hidden="true" focusable="false" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2" />
      <ellipse cx="12" cy="12" rx="10" ry="4" />
      <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)" />
      <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)" />
    </svg>
  );
}

function GlobeIcon({ color }: { color: string }) {
  return (
    <svg aria-hidden="true" focusable="false" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
    </svg>
  );
}

function FlaskIcon({ color }: { color: string }) {
  return (
    <svg aria-hidden="true" focusable="false" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 3h6v5l4 9H5l4-9V3z" />
      <line x1="9" y1="3" x2="15" y2="3" />
      <path d="M7 17h10" />
    </svg>
  );
}

function CellIcon({ color }: { color: string }) {
  return (
    <svg aria-hidden="true" focusable="false" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="12" rx="10" ry="8" />
      <circle cx="12" cy="12" r="3" />
      <circle cx="12" cy="12" r="1" fill={color} />
    </svg>
  );
}

function BookIcon({ color }: { color: string }) {
  return (
    <svg aria-hidden="true" focusable="false" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
    </svg>
  );
}

function DnaIcon({ color }: { color: string }) {
  return (
    <svg aria-hidden="true" focusable="false" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 15c6.667-6 13.333 0 20-6" />
      <path d="M9 22c1.798-1.998 2.518-3.995 2.807-5.993" />
      <path d="M15 2c-1.798 1.998-2.518 3.995-2.807 5.993" />
      <path d="M2 9c6.667 6 13.333 0 20 6" />
    </svg>
  );
}

function SubjectIcon({ type, color }: { type: SubjectConfig["icon"]; color: string }) {
  switch (type) {
    case "leaf": return <LeafIcon color={color} />;
    case "calc": return <CalcIcon color={color} />;
    case "atom": return <AtomIcon color={color} />;
    case "globe": return <GlobeIcon color={color} />;
    case "flask": return <FlaskIcon color={color} />;
    case "cell": return <CellIcon color={color} />;
    case "book": return <BookIcon color={color} />;
    case "dna": return <DnaIcon color={color} />;
    default: {
      const _exhaustive: never = type;
      return _exhaustive;
    }
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getGradeBand(gradeId: string): "middle" | "hs_lower" | "hs_upper" | null {
  const num = parseInt(gradeId.replace("grade", ""), 10);
  if (num >= 6 && num <= 8) return "middle";
  if (num >= 9 && num <= 10) return "hs_lower";
  if (num >= 11 && num <= 12) return "hs_upper";
  return null;
}

function isSupportedGrade(gradeId: string): boolean {
  return getGradeBand(gradeId) === "middle";
}

function getSubjectsForGrade(gradeId: string): readonly SubjectConfig[] {
  switch (gradeId) {
    case "grade6": return GRADE6_SUBJECTS;
    case "grade7": return GRADE7_SUBJECTS;
    case "grade8": return GRADE8_SUBJECTS;
    default: {
      const band = getGradeBand(gradeId);
      switch (band) {
        case "hs_lower": return HIGH_SCHOOL_LOWER_SUBJECTS;
        case "hs_upper": return HIGH_SCHOOL_UPPER_SUBJECTS;
        default: return [];
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Navbar() {
  const router = useRouter();

  return (
    <nav
      className="sticky top-0 z-50 flex items-center justify-between px-10 py-4"
      style={{
        background: "rgba(10,29,55,0.95)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <div className="flex items-center gap-2.5">
        <div
          className="flex items-center justify-center w-9 h-9 rounded-[10px] text-white text-base font-extrabold"
          style={{ background: "linear-gradient(135deg, #007AFF, #0056b3)" }}
        >
          L
        </div>
        <span className="text-white font-bold text-lg" style={{ letterSpacing: "-0.02em" }}>
          LUNA Tutor
        </span>
      </div>
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push("/upload")}
          className="text-white/70 text-sm font-medium px-4 py-2 rounded-lg hover:text-white hover:bg-white/5 transition-colors bg-transparent border-none cursor-pointer"
          style={{ fontFamily: "inherit" }}
        >
          Upload Worksheet
        </button>
        <button
          onClick={() => router.push("/flash-cards")}
          className="text-white/70 text-sm font-medium px-4 py-2 rounded-lg hover:text-white hover:bg-white/5 transition-colors bg-transparent border-none cursor-pointer"
          style={{ fontFamily: "inherit" }}
        >
          Flash Cards
        </button>
        <button
          onClick={() => router.push("/reviews")}
          className="text-white/70 text-sm font-medium px-4 py-2 rounded-lg hover:text-white hover:bg-white/5 transition-colors bg-transparent border-none cursor-pointer"
          style={{ fontFamily: "inherit" }}
        >
          All Reviews
        </button>
        <button
          disabled
          aria-label="Demo user"
          className="text-white/70 text-sm font-medium px-5 py-2 rounded-lg"
          style={{ border: "1.5px solid rgba(255,255,255,0.15)", cursor: "default" }}
        >
          User — Demo
        </button>
      </div>
    </nav>
  );
}

function HeroSection() {
  return (
    <section className="relative overflow-hidden text-center" style={{ padding: "80px 20px 60px" }}>
      {/* Background orbs */}
      <div
        className="absolute pointer-events-none rounded-full"
        style={{
          top: -120, right: -80, width: 400, height: 400,
          background: "radial-gradient(circle, rgba(0,122,255,0.12) 0%, transparent 70%)",
        }}
      />
      <div
        className="absolute pointer-events-none rounded-full"
        style={{
          bottom: -100, left: -60, width: 300, height: 300,
          background: "radial-gradient(circle, rgba(111,66,193,0.08) 0%, transparent 70%)",
        }}
      />

      <div className="relative z-10">
        <h1
          className="text-white font-extrabold mb-5"
          style={{ fontSize: "clamp(2.4rem, 5vw, 3.6rem)", letterSpacing: "-0.03em", lineHeight: 1.1 }}
        >
          Personalized AI Tutoring
          <br />
          <span
            style={{
              background: "linear-gradient(90deg, #007AFF, #56B4FF, #007AFF)",
              backgroundSize: "200% auto",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              animation: "shimmer 4s linear infinite",
            }}
          >
            for Every Student
          </span>
        </h1>
        <p
          className="mx-auto font-normal"
          style={{ color: "#8899b0", fontSize: "clamp(1rem, 2vw, 1.15rem)", maxWidth: 560, lineHeight: 1.7 }}
        >
          Learn with a real-time AI video avatar. Pick your grade level,
          choose a subject, and start an interactive tutoring session — voice in, voice out.
        </p>
      </div>
    </section>
  );
}

interface GradeGroupProps {
  title: string;
  grades: readonly Grade[];
  selectedGrade: string | null;
  hoveredGrade: string | null;
  onGradeClick: (id: string) => void;
  onHover: (id: string | null) => void;
  indexOffset: number;
  demo?: boolean;
}

function GradeGroup({
  title,
  grades,
  selectedGrade,
  hoveredGrade,
  onGradeClick,
  onHover,
  indexOffset,
  demo = false,
}: GradeGroupProps) {
  return (
    <div className="flex flex-col items-center gap-3">
      <span
        className="text-[11px] font-semibold uppercase tracking-wider"
        style={{ color: demo ? "#4a5568" : "#6a7f99" }}
      >
        {title}
      </span>
      <div className="flex gap-3 flex-wrap justify-center" role="radiogroup" aria-label={title}>
        {grades.map((g, i) => {
          const isActive = selectedGrade === g.id;
          const isHovered = hoveredGrade === g.id;
          return (
            <button
              key={g.id}
              role="radio"
              aria-checked={isActive}
              onClick={() => onGradeClick(g.id)}
              onMouseEnter={() => onHover(g.id)}
              onMouseLeave={() => onHover(null)}
              className={demo ? "" : "cursor-pointer"}
              title={demo ? "Coming soon" : undefined}
              aria-label={`${g.label}${demo ? " (coming soon)" : ""}`}
              style={{
                background: demo
                  ? isActive
                    ? "linear-gradient(135deg, #4a5568, #2d3748)"
                    : isHovered
                      ? "rgba(255,255,255,0.05)"
                      : "rgba(255,255,255,0.02)"
                  : isActive
                    ? "linear-gradient(135deg, #007AFF, #0056b3)"
                    : isHovered
                      ? "rgba(255,255,255,0.08)"
                      : "rgba(255,255,255,0.04)",
                border: demo
                  ? isActive
                    ? "2px solid #4a5568"
                    : "2px solid rgba(255,255,255,0.05)"
                  : isActive
                    ? "2px solid #007AFF"
                    : "2px solid rgba(255,255,255,0.08)",
                borderRadius: 14, padding: "20px 32px",
                opacity: demo ? 0.6 : 1,
                transition: "all 0.3s cubic-bezier(0.4,0,0.2,1)",
                transform: isActive ? "translateY(-4px)" : isHovered ? "translateY(-2px)" : "none",
                boxShadow: demo
                  ? "none"
                  : isActive
                    ? "0 12px 32px rgba(0,122,255,0.25)"
                    : isHovered
                      ? "0 6px 20px rgba(0,0,0,0.2)"
                      : "none",
                minWidth: 110, fontFamily: "inherit",
                animation: `float-in 0.5s ease ${(indexOffset + i) * 0.08}s both`,
              }}
            >
              <div
                className="font-extrabold mb-1"
                style={{
                  fontSize: 28,
                  color: demo
                    ? isActive ? "#a0aec0" : "#718096"
                    : isActive ? "#fff" : "#c0d0e0",
                  letterSpacing: "-0.02em",
                }}
              >
                {g.number}
              </div>
              <div
                className="font-medium"
                style={{
                  fontSize: 13,
                  color: demo
                    ? isActive ? "rgba(160,174,192,0.85)" : "#4a5568"
                    : isActive ? "rgba(255,255,255,0.85)" : "#6a7f99",
                }}
              >
                {g.label}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function FeaturesRow() {
  return (
    <section className="mx-auto" style={{ padding: "20px 20px 80px", maxWidth: 900 }}>
      <div className="flex justify-center gap-6 flex-wrap">
        {FEATURES.map((f, i) => (
          <div
            key={f.title}
            className="text-center"
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 16, padding: "28px 24px",
              flex: "1 1 200px", maxWidth: 260,
              animation: `float-in 0.5s ease ${0.3 + i * 0.1}s both`,
            }}
          >
            <div
              className="text-[28px] mb-3"
              style={{ animation: "gentle-float 3s ease-in-out infinite", animationDelay: `${i * 0.5}s` }}
            >
              <span role="img" aria-label={f.label}>{f.icon}</span>
            </div>
            <div className="font-semibold text-[15px] mb-1.5" style={{ color: "#e0e8f0" }}>
              {f.title}
            </div>
            <div className="text-[13px] leading-relaxed" style={{ color: "#6a7f99" }}>
              {f.desc}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer
      className="flex justify-between items-center flex-wrap gap-3"
      style={{ borderTop: "1px solid rgba(255,255,255,0.06)", padding: "24px 40px" }}
    >
      <span className="text-[13px]" style={{ color: "#3d506a" }}>
        LUNA Tutor
      </span>
      <div className="flex gap-5">
        {(["Terms", "Privacy", "Help"] as const).map((link) => (
          <span
            key={link}
            className="text-[13px]"
            style={{ color: "#506480" }}
          >
            {link}
          </span>
        ))}
      </div>
    </footer>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Flash Card Stats Section
// ---------------------------------------------------------------------------

function FlashCardSection({
  stats,
  loading,
}: {
  readonly stats: Readonly<Record<string, FlashCardStats>>;
  readonly loading: boolean;
}) {
  const router = useRouter();
  const subjects = Object.entries(stats);

  if (loading) return null;
  if (subjects.length === 0) return null;

  return (
    <section className="mx-auto" style={{ padding: "0 20px 40px", maxWidth: 900 }}>
      <div className="flex items-center justify-between mb-4">
        <p
          className="uppercase font-semibold"
          style={{ color: "#506480", fontSize: 12, letterSpacing: "0.15em" }}
        >
          Flash Cards
        </p>
      </div>
      <div className="flex gap-4 flex-wrap">
        {subjects.map(([subject, stat]) => {
          const total = stat.total;
          if (total === 0) return null;
          const knownPct = Math.round((stat.known / total) * 100);
          const learningPct = Math.round((stat.learning / total) * 100);
          return (
            <div
              key={subject}
              className="flex-1 min-w-[200px] max-w-[280px] bg-gray-800/40 border border-gray-700 rounded-lg p-4"
            >
              <p className="text-sm font-medium text-white capitalize mb-2">
                {subject.replaceAll("_", " ")}
              </p>
              <p className="text-xs text-gray-500 mb-2">{total} cards</p>
              <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden flex">
                <div
                  className="h-full bg-green-400"
                  style={{ width: `${knownPct}%` }}
                />
                <div
                  className="h-full bg-amber-400"
                  style={{ width: `${learningPct}%` }}
                />
              </div>
              <div className="flex gap-3 mt-2 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  {stat.known} known
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  {stat.learning} learning
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-gray-500" />
                  {stat.new} new
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}


// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function Home() {
  const router = useRouter();
  const [selectedGrade, setSelectedGrade] = useState<string | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null);
  const [hoveredGrade, setHoveredGrade] = useState<string | null>(null);
  const [hoveredSubject, setHoveredSubject] = useState<Subject | null>(null);
  const [subjectsVisible, setSubjectsVisible] = useState(false);
  const [sessions, setSessions] = useState<readonly Session[]>([]);
  const [flashCardStats, setFlashCardStats] = useState<
    Readonly<Record<string, FlashCardStats>>
  >({});
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [toasts, setToasts] = useState<readonly Toast[]>([]);

  const subjects = useMemo(
    () => (selectedGrade ? getSubjectsForGrade(selectedGrade) : []),
    [selectedGrade],
  );

  const isDemoGrade = selectedGrade ? !isSupportedGrade(selectedGrade) : false;
  const canStartSession = Boolean(selectedSubject && selectedGrade && !isDemoGrade);

  // Fetch sessions and flash card stats on mount
  useEffect(() => {
    const userId = getUserId();
    if (!userId) {
      setDashboardLoading(false);
      return;
    }

    const validUserId: string = userId;
    let cancelled = false;

    async function fetchDashboardData() {
      try {
        const [sessionsData, statsData] = await Promise.allSettled([
          listSessions(validUserId),
          getFlashCardStats(validUserId),
        ]);

        if (!cancelled) {
          if (sessionsData.status === "fulfilled") {
            setSessions(sessionsData.value);
          } else {
            logger.warn("sessions_fetch_failed", {
              error: String(sessionsData.reason),
            });
          }

          if (statsData.status === "fulfilled") {
            setFlashCardStats(statsData.value);
          } else {
            logger.warn("flash_card_stats_fetch_failed", {
              error: String(statsData.reason),
            });
          }

          setDashboardLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          logger.error("dashboard_fetch_failed", { error: String(err) });
          setDashboardLoading(false);
        }
      }
    }

    fetchDashboardData();
    return () => {
      cancelled = true;
    };
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Reset subject animation when grade changes
  useEffect(() => {
    if (selectedGrade) {
      setSubjectsVisible(false);
      const t = setTimeout(() => setSubjectsVisible(true), 80);
      return () => clearTimeout(t);
    }
  }, [selectedGrade]);

  const handleGradeClick = useCallback((id: string) => {
    setSelectedSubject(null);
    if (selectedGrade === id) {
      setSelectedGrade(null);
    } else {
      setSelectedGrade(id);
      // Auto-select when there's only one subject for this grade
      const gradeSubjects = getSubjectsForGrade(id);
      if (gradeSubjects.length === 1) {
        setSelectedSubject(gradeSubjects[0].subject);
      }
    }
    logger.debug("grade_clicked", { gradeId: id });
  }, [selectedGrade]);

  const handleSubjectClick = useCallback((subject: Subject) => {
    setSelectedSubject(subject);
    logger.debug("subject_clicked", { subject });
  }, []);

  const handleBack = useCallback(() => {
    setSelectedGrade(null);
    setSelectedSubject(null);
    logger.debug("back_to_grades");
  }, []);

  const handleStart = useCallback(() => {
    if (!selectedSubject) return;
    const grade = ALL_GRADES.find((g) => g.id === selectedGrade);
    logger.info("session_started", { subject: selectedSubject, grade: grade?.label });
    router.push(`/session?subject=${encodeURIComponent(selectedSubject)}&grade=${grade?.number ?? ""}`);
  }, [selectedSubject, selectedGrade, router]);

  const gradeLabel = selectedGrade
    ? ALL_GRADES.find((g) => g.id === selectedGrade)?.label ?? ""
    : "";

  return (
    <div className="min-h-screen" style={{ background: "#0a1d37" }}>
      <Navbar />
      <HeroSection />

      {/* Step 1 — Grade Selection (grouped) */}
      <section className="mx-auto" style={{ padding: "0 20px 40px", maxWidth: 960 }}>
        <p
          className="text-center uppercase font-semibold mb-8"
          style={{ color: "#506480", fontSize: 12, letterSpacing: "0.15em" }}
        >
          Step 1 — Select Your Level
        </p>
        <div className="flex justify-center gap-10 flex-wrap">
          {/* Middle School group */}
          <GradeGroup
            title="Middle School"
            grades={MIDDLE_SCHOOL}
            selectedGrade={selectedGrade}
            hoveredGrade={hoveredGrade}
            onGradeClick={handleGradeClick}
            onHover={setHoveredGrade}
            indexOffset={0}
          />
          {/* High School group */}
          <GradeGroup
            title="High School"
            grades={HIGH_SCHOOL}
            selectedGrade={selectedGrade}
            hoveredGrade={hoveredGrade}
            onGradeClick={handleGradeClick}
            onHover={setHoveredGrade}
            indexOffset={MIDDLE_SCHOOL.length}
            demo
          />
        </div>
      </section>

      {/* Step 2 — Subject Selection (shown when grade selected) */}
      {selectedGrade && (
        <section className="mx-auto" style={{ padding: "0 20px 60px", maxWidth: 900 }}>
          <p
            className="text-center uppercase font-semibold mb-6"
            style={{ color: "#506480", fontSize: 12, letterSpacing: "0.15em" }}
          >
            Step 2 — Choose a Subject for {gradeLabel}
          </p>

          <div className="flex justify-center gap-4 flex-wrap" role="radiogroup" aria-label="Subject">
            {subjects.map((subj, i) => {
              const isChosen = !isDemoGrade && selectedSubject === subj.subject;
              const isHovered = !isDemoGrade && hoveredSubject === subj.subject;
              const showHighlight = isChosen || isHovered;
              return (
                <button
                  key={subj.subject}
                  role="radio"
                  aria-checked={isChosen}
                  aria-disabled={isDemoGrade}
                  aria-label={isDemoGrade ? `${subj.name} — Demo, coming soon` : subj.name}
                  onClick={isDemoGrade ? undefined : () => handleSubjectClick(subj.subject)}
                  onMouseEnter={isDemoGrade ? undefined : () => setHoveredSubject(subj.subject)}
                  onMouseLeave={isDemoGrade ? undefined : () => setHoveredSubject(null)}
                  className={isDemoGrade ? "text-center" : "cursor-pointer text-center"}
                  style={{
                    position: "relative",
                    background: isDemoGrade
                      ? "rgba(255,255,255,0.02)"
                      : isChosen
                        ? `linear-gradient(135deg, ${subj.color}15, ${subj.color}08)`
                        : "rgba(255,255,255,0.03)",
                    border: isDemoGrade
                      ? "2px solid rgba(255,255,255,0.04)"
                      : showHighlight
                        ? `2px solid ${subj.color}`
                        : "2px solid rgba(255,255,255,0.06)",
                    borderRadius: 16, padding: "28px 24px",
                    minWidth: 180, maxWidth: 200, fontFamily: "inherit",
                    transition: "all 0.3s ease",
                    transform: isHovered && !isChosen ? "translateY(-4px)" : "none",
                    boxShadow: isHovered && !isChosen ? `0 8px 24px ${subj.color}20` : "none",
                    animation: subjectsVisible ? `fade-slide-up 0.4s ease ${i * 0.1}s both` : "none",
                    opacity: isDemoGrade ? 0.45 : subjectsVisible ? 1 : 0,
                    cursor: isDemoGrade ? "default" : "pointer",
                    filter: isDemoGrade ? "grayscale(0.7)" : "none",
                  }}
                >
                  {isDemoGrade && (
                    <span
                      aria-hidden="true"
                      style={{
                        position: "absolute",
                        top: 8,
                        right: 8,
                        background: "rgba(100,116,139,0.5)",
                        color: "#cbd5e1",
                        fontSize: 10,
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        padding: "2px 8px",
                        borderRadius: 6,
                        lineHeight: "18px",
                      }}
                    >
                      DEMO
                    </span>
                  )}
                  <div
                    className="flex items-center justify-center mx-auto mb-3.5"
                    style={{ width: 52, height: 52, borderRadius: 14, background: isDemoGrade ? "rgba(255,255,255,0.04)" : subj.bg }}
                  >
                    <SubjectIcon type={subj.icon} color={isDemoGrade ? "#4a5568" : subj.color} />
                  </div>
                  <div className="font-bold mb-1" style={{ fontSize: 16, color: isDemoGrade ? "#718096" : "#e0e8f0" }}>
                    {subj.name}
                  </div>
                  <div className="font-normal" style={{ fontSize: 13, color: isDemoGrade ? "#4a5568" : "#6a7f99" }}>
                    {subj.topic}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Start Button — only for active (non-demo) grades */}
          {canStartSession && (
            <div
              className="text-center"
              style={{ marginTop: 36, animation: "fade-slide-up 0.4s ease both" }}
            >
              <button
                onClick={handleStart}
                className="text-white border-none cursor-pointer font-semibold inline-flex items-center gap-2.5 transition-all duration-300 hover:-translate-y-0.5"
                style={{
                  background: "linear-gradient(135deg, #007AFF, #0056b3)",
                  borderRadius: 12, padding: "16px 48px", fontSize: 16,
                  fontFamily: "inherit",
                  boxShadow: "0 8px 32px rgba(0,122,255,0.3)",
                }}
              >
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ background: "#28A745", animation: "pulse-dot 1.5s infinite" }}
                />
                Start Tutoring Session
              </button>
              <p className="mt-3" style={{ color: "#506480", fontSize: 13 }}>
                {subjects.find((s) => s.subject === selectedSubject)?.name} — {gradeLabel}
              </p>
            </div>
          )}
        </section>
      )}

      {/* Features Row (shown when no grade selected) */}
      {!selectedGrade && <FeaturesRow />}

      {/* Flash Card Stats (shown when no grade selected and data exists) */}
      {!selectedGrade && (
        <FlashCardSection stats={flashCardStats} loading={dashboardLoading} />
      )}

      <Footer />

      {/* Toast Notifications */}
      <ToastNotification toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
