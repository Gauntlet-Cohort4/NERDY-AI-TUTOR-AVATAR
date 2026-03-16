"use client";

import AvatarDisplay from "./AvatarDisplay";

interface AvatarPiPProps {
  readonly isActive: boolean;
}

/**
 * Inline mini-avatar shown when the whiteboard is active.
 * Renders as a small rounded element that can be placed anywhere in the layout.
 */
export default function AvatarPiP({ isActive }: AvatarPiPProps) {
  if (!isActive) return null;

  return (
    <div className="w-52 rounded-xl overflow-hidden shadow-2xl border-2 border-gray-700 flex-shrink-0">
      <AvatarDisplay />
    </div>
  );
}
