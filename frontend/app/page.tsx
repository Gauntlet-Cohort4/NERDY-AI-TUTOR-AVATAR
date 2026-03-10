"use client";

import { useRouter } from "next/navigation";
import SubjectSelector from "@/components/SubjectSelector";
import type { Subject } from "@/lib/types";

export default function Home() {
  const router = useRouter();

  function handleSubjectSelect(subject: Subject) {
    router.push(`/session?subject=${encodeURIComponent(subject)}`);
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-10 px-4 py-16 bg-gray-50">
      <div className="text-center">
        <h1 className="text-5xl font-bold text-gray-900 tracking-tight">
          Nerdy AI Tutor
        </h1>
        <p className="mt-4 text-lg text-gray-600 max-w-md mx-auto">
          Learn with a real-time AI video avatar. Pick a subject below and start
          an interactive tutoring session — voice in, voice out.
        </p>
      </div>

      <div className="flex flex-col items-center gap-4">
        <p className="text-sm font-medium text-gray-500 uppercase tracking-widest">
          Choose a subject
        </p>
        <SubjectSelector onSelect={handleSubjectSelect} />
      </div>
    </main>
  );
}
