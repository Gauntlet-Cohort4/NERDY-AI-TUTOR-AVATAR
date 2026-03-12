interface SessionControlsProps {
  isConnected: boolean;
  onStart: () => void;
  onEnd: () => void;
  metricsVisible: boolean;
  onToggleMetrics: () => void;
  transcriptVisible: boolean;
  onToggleTranscript: () => void;
}

export default function SessionControls({
  isConnected,
  onStart,
  onEnd,
  metricsVisible,
  onToggleMetrics,
  transcriptVisible,
  onToggleTranscript,
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
      <button
        onClick={onToggleMetrics}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          metricsVisible
            ? "bg-blue-600 text-white hover:bg-blue-700"
            : "bg-gray-700 text-gray-300 hover:bg-gray-600"
        }`}
        title={metricsVisible ? "Hide latency metrics" : "Show latency metrics"}
      >
        {metricsVisible ? (
          <span className="flex items-center gap-1.5">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z" />
              <path fillRule="evenodd" d="M.664 10.59a1.651 1.651 0 0 1 0-1.186A10.004 10.004 0 0 1 10 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0 1 10 17c-4.257 0-7.893-2.66-9.336-6.41ZM14 10a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z" clipRule="evenodd" />
            </svg>
            Hide Metrics
          </span>
        ) : (
          <span className="flex items-center gap-1.5">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M3.28 2.22a.75.75 0 0 0-1.06 1.06l14.5 14.5a.75.75 0 1 0 1.06-1.06l-1.745-1.745a10.029 10.029 0 0 0 3.3-4.38 1.651 1.651 0 0 0 0-1.185A10.004 10.004 0 0 0 9.999 3a9.956 9.956 0 0 0-4.744 1.194L3.28 2.22ZM7.752 6.69l1.092 1.092a2.5 2.5 0 0 1 3.374 3.373l1.091 1.092a4 4 0 0 0-5.557-5.557Z" clipRule="evenodd" />
              <path d="m10.748 13.93 2.523 2.523a9.987 9.987 0 0 1-3.27.547c-4.258 0-7.894-2.66-9.337-6.41a1.651 1.651 0 0 1 0-1.186A10.007 10.007 0 0 1 4.09 5.12L6.3 7.33a4 4 0 0 0 4.448 4.448Z" />
            </svg>
            Show Metrics
          </span>
        )}
      </button>
      <button
        onClick={onToggleTranscript}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          transcriptVisible
            ? "bg-purple-600 text-white hover:bg-purple-700"
            : "bg-gray-700 text-gray-300 hover:bg-gray-600"
        }`}
        title={transcriptVisible ? "Hide transcript" : "Show transcript"}
      >
        <span className="flex items-center gap-1.5">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path fillRule="evenodd" d="M10 2c-2.236 0-4.43.18-6.57.524C1.993 2.755 1 4.014 1 5.426v5.148c0 1.413.993 2.67 2.43 2.902 1.168.188 2.352.327 3.55.414.28.02.521.18.642.413l1.713 3.293a.75.75 0 0 0 1.33 0l1.713-3.293a.783.783 0 0 1 .642-.413 41.102 41.102 0 0 0 3.55-.414c1.437-.231 2.43-1.49 2.43-2.902V5.426c0-1.413-.993-2.67-2.43-2.902A41.289 41.289 0 0 0 10 2ZM6.75 6a.75.75 0 0 0 0 1.5h6.5a.75.75 0 0 0 0-1.5h-6.5Zm0 2.5a.75.75 0 0 0 0 1.5h3.5a.75.75 0 0 0 0-1.5h-3.5Z" clipRule="evenodd" />
          </svg>
          {transcriptVisible ? "Hide" : "Show"} Transcript
        </span>
      </button>
    </div>
  );
}
