interface SessionControlsProps {
  isConnected: boolean;
  onStart: () => void;
  onEnd: () => void;
}

export default function SessionControls({
  isConnected,
  onStart,
  onEnd,
}: SessionControlsProps) {
  return (
    <div className="flex gap-2">
      {!isConnected ? (
        <button
          onClick={onStart}
          className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
        >
          Start Session
        </button>
      ) : (
        <button
          onClick={onEnd}
          className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          End Session
        </button>
      )}
    </div>
  );
}
