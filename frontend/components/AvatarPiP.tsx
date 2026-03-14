"use client";

import AvatarDisplay from "./AvatarDisplay";

interface AvatarPiPProps {
  isActive: boolean;
}

export default function AvatarPiP({ isActive }: AvatarPiPProps) {
  if (!isActive) return null;

  return (
    <div className="fixed bottom-24 right-6 z-30 w-48 h-48 rounded-xl overflow-hidden shadow-2xl border-2 border-gray-700 transition-all duration-500 ease-in-out">
      <AvatarDisplay />
    </div>
  );
}
