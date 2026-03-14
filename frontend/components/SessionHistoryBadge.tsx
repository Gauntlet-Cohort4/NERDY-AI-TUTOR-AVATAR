interface SessionHistoryBadgeProps {
  readonly count: number;
  readonly hasGenerating: boolean;
}

export default function SessionHistoryBadge({
  count,
  hasGenerating,
}: SessionHistoryBadgeProps) {
  if (count === 0 && !hasGenerating) return null;

  return (
    <div className="absolute top-2 right-2 flex items-center gap-1">
      {hasGenerating ? (
        <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
      ) : count > 0 ? (
        <span className="w-2.5 h-2.5 rounded-full bg-green-400" />
      ) : null}
    </div>
  );
}
