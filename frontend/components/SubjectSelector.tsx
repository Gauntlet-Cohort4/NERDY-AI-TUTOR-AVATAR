import type { Subject } from "@/lib/types";

interface SubjectSelectorProps {
  onSelect: (subject: Subject) => void;
  selected?: Subject;
}

export default function SubjectSelector({
  onSelect,
  selected,
}: SubjectSelectorProps) {
  const subjects: { id: Subject; label: string; description: string }[] = [
    { id: "biology", label: "Biology", description: "Photosynthesis" },
    { id: "math", label: "Math", description: "Fractions" },
    { id: "physics", label: "Physics", description: "Newton's Third Law" },
  ];

  return (
    <div className="flex gap-4">
      {subjects.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          className={`px-4 py-2 rounded-lg border ${
            selected === s.id
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-gray-400"
          }`}
        >
          <div className="font-semibold">{s.label}</div>
          <div className="text-sm text-gray-500">{s.description}</div>
        </button>
      ))}
    </div>
  );
}
