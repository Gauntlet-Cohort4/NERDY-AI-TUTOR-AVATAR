"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createLogger } from "@/lib/logger";
import type { Subject } from "@/lib/types";

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
  readonly icon: "leaf" | "calc" | "atom";
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

// Same three subjects for every grade (demo mode)
const SUBJECTS: readonly SubjectConfig[] = [
  { name: "Biology", subject: "biology", topic: "Life Sciences", icon: "leaf", color: "#28A745", bg: "rgba(40,167,69,0.08)" },
  { name: "Math", subject: "math", topic: "Mathematics", icon: "calc", color: "#6F42C1", bg: "rgba(111,66,193,0.08)" },
  { name: "Physics", subject: "physics", topic: "Physical Sciences", icon: "atom", color: "#FD7E14", bg: "rgba(253,126,20,0.08)" },
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

function SubjectIcon({ type, color }: { type: SubjectConfig["icon"]; color: string }) {
  switch (type) {
    case "leaf": return <LeafIcon color={color} />;
    case "calc": return <CalcIcon color={color} />;
    case "atom": return <AtomIcon color={color} />;
    default: {
      const _exhaustive: never = type;
      return _exhaustive;
    }
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LiveIndicator() {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold"
      style={{ background: "rgba(40,167,69,0.1)", color: "#28A745" }}
    >
      <span
        className="inline-block w-[7px] h-[7px] rounded-full"
        style={{ background: "#28A745", animation: "pulse-dot 1.5s infinite" }}
      />
      AI Ready
    </span>
  );
}

function Navbar() {
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
          N
        </div>
        <span className="text-white font-bold text-lg" style={{ letterSpacing: "-0.02em" }}>
          Nerdy AI Tutor
        </span>
      </div>
      <span
        className="text-white text-sm font-medium px-5 py-2 rounded-lg"
        style={{ border: "1.5px solid rgba(255,255,255,0.2)" }}
        aria-hidden="true"
      >
        Sign In
      </span>
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
        <div className="mb-5">
          <LiveIndicator />
        </div>
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
}

function GradeGroup({
  title,
  grades,
  selectedGrade,
  hoveredGrade,
  onGradeClick,
  onHover,
  indexOffset,
}: GradeGroupProps) {
  return (
    <div className="flex flex-col items-center gap-3">
      <span
        className="text-[11px] font-semibold uppercase tracking-wider"
        style={{ color: "#6a7f99" }}
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
              className="cursor-pointer"
              style={{
                background: isActive
                  ? "linear-gradient(135deg, #007AFF, #0056b3)"
                  : isHovered
                    ? "rgba(255,255,255,0.08)"
                    : "rgba(255,255,255,0.04)",
                border: isActive
                  ? "2px solid #007AFF"
                  : "2px solid rgba(255,255,255,0.08)",
                borderRadius: 14, padding: "20px 32px",
                transition: "all 0.3s cubic-bezier(0.4,0,0.2,1)",
                transform: isActive ? "translateY(-4px)" : isHovered ? "translateY(-2px)" : "none",
                boxShadow: isActive
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
                  fontSize: 28, color: isActive ? "#fff" : "#c0d0e0",
                  letterSpacing: "-0.02em",
                }}
              >
                {g.number}
              </div>
              <div
                className="font-medium"
                style={{
                  fontSize: 13,
                  color: isActive ? "rgba(255,255,255,0.85)" : "#6a7f99",
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
        Nerdy AI Tutor
      </span>
      <div className="flex gap-5">
        {(["Terms", "Privacy", "Help"] as const).map((link) => (
          <a
            key={link}
            href="#"
            className="text-[13px] no-underline transition-colors duration-200 hover:text-[#007AFF]"
            style={{ color: "#506480" }}
            onClick={(e) => e.preventDefault()}
          >
            {link}
          </a>
        ))}
      </div>
    </footer>
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
    setSelectedGrade((prev) => (prev === id ? null : id));
    logger.debug("grade_clicked", { gradeId: id });
  }, []);

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
    router.push(`/session?subject=${encodeURIComponent(selectedSubject)}`);
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
          />
        </div>
      </section>

      {/* Step 2 — Subject Selection (shown when grade selected) */}
      {selectedGrade && (
        <section className="mx-auto" style={{ padding: "0 20px 60px", maxWidth: 900 }}>
          {/* Back button */}
          <div className="text-center mb-4">
            <button
              onClick={handleBack}
              className="bg-transparent border-none cursor-pointer font-medium inline-flex items-center gap-1.5"
              style={{ color: "#007AFF", fontSize: 13, fontFamily: "inherit" }}
            >
              <span className="text-base">&larr;</span> Back to Grade Levels
            </button>
          </div>

          <p
            className="text-center uppercase font-semibold mb-6"
            style={{ color: "#506480", fontSize: 12, letterSpacing: "0.15em" }}
          >
            Step 2 — Choose a Subject for {gradeLabel}
          </p>

          <div className="flex justify-center gap-4 flex-wrap" role="radiogroup" aria-label="Subject">
            {SUBJECTS.map((subj, i) => {
              const isChosen = selectedSubject === subj.subject;
              const isHovered = hoveredSubject === subj.subject;
              const showHighlight = isChosen || isHovered;
              return (
                <button
                  key={subj.subject}
                  role="radio"
                  aria-checked={isChosen}
                  onClick={() => handleSubjectClick(subj.subject)}
                  onMouseEnter={() => setHoveredSubject(subj.subject)}
                  onMouseLeave={() => setHoveredSubject(null)}
                  className="cursor-pointer text-center"
                  style={{
                    background: isChosen
                      ? `linear-gradient(135deg, ${subj.color}15, ${subj.color}08)`
                      : "rgba(255,255,255,0.03)",
                    border: showHighlight
                      ? `2px solid ${subj.color}`
                      : "2px solid rgba(255,255,255,0.06)",
                    borderRadius: 16, padding: "28px 24px",
                    minWidth: 180, maxWidth: 200, fontFamily: "inherit",
                    transition: "all 0.3s ease",
                    transform: isHovered && !isChosen ? "translateY(-4px)" : "none",
                    boxShadow: isHovered && !isChosen ? `0 8px 24px ${subj.color}20` : "none",
                    animation: subjectsVisible ? `fade-slide-up 0.4s ease ${i * 0.1}s both` : "none",
                    opacity: subjectsVisible ? 1 : 0,
                  }}
                >
                  <div
                    className="flex items-center justify-center mx-auto mb-3.5"
                    style={{ width: 52, height: 52, borderRadius: 14, background: subj.bg }}
                  >
                    <SubjectIcon type={subj.icon} color={subj.color} />
                  </div>
                  <div className="font-bold mb-1" style={{ fontSize: 16, color: "#e0e8f0" }}>
                    {subj.name}
                  </div>
                  <div className="font-normal" style={{ fontSize: 13, color: "#6a7f99" }}>
                    {subj.topic}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Start Button */}
          {selectedSubject && (
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
                {SUBJECTS.find((s) => s.subject === selectedSubject)?.name} — {gradeLabel}
              </p>
            </div>
          )}
        </section>
      )}

      {/* Features Row (shown when no grade selected) */}
      {!selectedGrade && <FeaturesRow />}

      <Footer />
    </div>
  );
}
