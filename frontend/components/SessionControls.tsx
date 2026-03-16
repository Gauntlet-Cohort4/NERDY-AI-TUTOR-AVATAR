"use client";

import { useCallback, useState } from "react";
import { useTrackToggle } from "@livekit/components-react";
import { Track } from "livekit-client";
import { createLogger } from "@/lib/logger";

const logger = createLogger("SessionControls");

interface SessionControlsProps {
  readonly isConnected: boolean;
  readonly onStart: () => void;
  readonly onEnd: () => void;
  readonly metricsVisible: boolean;
  readonly onToggleMetrics: () => void;
  readonly transcriptVisible: boolean;
  readonly onToggleTranscript: () => void;
  readonly volume: number;
  readonly onVolumeChange: (v: number) => void;
}

function MicToggle() {
  const { enabled, toggle } = useTrackToggle({ source: Track.Source.Microphone });

  const handleToggle = () => {
    toggle();
    logger.info("mic_toggled", { muted: enabled });
  };

  return (
    <button
      onClick={handleToggle}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
        enabled
          ? "bg-green-600 text-white hover:bg-green-700"
          : "bg-yellow-600 text-white hover:bg-yellow-700"
      }`}
      title={enabled ? "Mute microphone" : "Unmute microphone"}
    >
      <span className="flex items-center gap-1.5">
        {enabled ? (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M7 4a3 3 0 0 1 6 0v6a3 3 0 1 1-6 0V4Z" />
            <path d="M5.5 9.643a.75.75 0 0 0-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 0 0 0 1.5h4.5a.75.75 0 0 0 0-1.5h-1.5v-1.546A6.001 6.001 0 0 0 16 10v-.357a.75.75 0 0 0-1.5 0V10a4.5 4.5 0 0 1-9 0v-.357Z" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M17.78 2.22a.75.75 0 0 0-1.06 0l-3.22 3.22V4a3 3 0 0 0-6 0v6c0 .09 0 .18.02.27L4.3 13.48A5.97 5.97 0 0 1 4 12v-.357a.75.75 0 0 0-1.5 0V12c0 1.54.58 2.94 1.53 4.01L2.22 17.78a.75.75 0 1 0 1.06 1.06l14.5-14.5a.75.75 0 0 0 0-1.06Z" />
            <path d="M15.5 11.643a.75.75 0 0 1 .75.75 5.97 5.97 0 0 1-.83 3.05l-1.09-1.09c.33-.57.52-1.22.57-1.9v-.06a.75.75 0 0 1 .75-.75ZM10.75 15.954V17.5h1.5a.75.75 0 0 1 0 1.5h-4.5a.75.75 0 0 1 0-1.5h1.5v-1.546a6.06 6.06 0 0 1-1.13-.195l1.2-1.2c.45.1.92.155 1.4.161a4.51 4.51 0 0 0 3.78-2.04l1.09 1.09A5.99 5.99 0 0 1 10.75 15.954Z" />
            <path d="M13 10V6.09L8.39 10.7c.44.53 1.1.87 1.84.93.08.01.16.01.25.01A3 3 0 0 0 13 10Z" />
          </svg>
        )}
        {enabled ? "Mic On" : "Mic Off"}
      </span>
    </button>
  );
}

function VolumeSlider({
  volume,
  onVolumeChange,
}: {
  readonly volume: number;
  readonly onVolumeChange: (v: number) => void;
}) {
  const [premuteVolume, setPremuteVolume] = useState(volume);
  const isMuted = volume === 0;

  const handleMuteToggle = useCallback(() => {
    if (isMuted) {
      onVolumeChange(premuteVolume > 0 ? premuteVolume : 0.8);
    } else {
      setPremuteVolume(volume);
      onVolumeChange(0);
    }
  }, [isMuted, volume, premuteVolume, onVolumeChange]);

  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = parseFloat(e.target.value);
      onVolumeChange(v);
      if (v > 0) setPremuteVolume(v);
    },
    [onVolumeChange],
  );

  return (
    <div className="flex items-center gap-1.5">
      <button
        onClick={handleMuteToggle}
        className="p-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
        title={isMuted ? "Unmute AI voice" : "Mute AI voice"}
      >
        {isMuted ? (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M10.047 3.062a.75.75 0 0 1 .453.688v12.5a.75.75 0 0 1-1.264.546L5.203 13H2.667a.75.75 0 0 1-.7-.48A6.985 6.985 0 0 1 1.5 10c0-.85.151-1.665.429-2.42a.75.75 0 0 1 .7-.58h2.564l4.033-3.796a.75.75 0 0 1 .811-.142Z" />
            <path d="m13.22 7.22 2-2a.75.75 0 1 1 1.06 1.06l-2 2 2 2a.75.75 0 1 1-1.06 1.06l-2-2-2 2a.75.75 0 0 1-1.06-1.06l2-2-2-2a.75.75 0 0 1 1.06-1.06l2 2Z" />
          </svg>
        ) : volume < 0.5 ? (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M10.047 3.062a.75.75 0 0 1 .453.688v12.5a.75.75 0 0 1-1.264.546L5.203 13H2.667a.75.75 0 0 1-.7-.48A6.985 6.985 0 0 1 1.5 10c0-.85.151-1.665.429-2.42a.75.75 0 0 1 .7-.58h2.564l4.033-3.796a.75.75 0 0 1 .811-.142Z" />
            <path d="M14.017 7.19a.75.75 0 0 1 1.044.193 4.004 4.004 0 0 1 0 4.435.75.75 0 1 1-1.237-.85 2.504 2.504 0 0 0 0-2.735.75.75 0 0 1 .193-1.044Z" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M10.047 3.062a.75.75 0 0 1 .453.688v12.5a.75.75 0 0 1-1.264.546L5.203 13H2.667a.75.75 0 0 1-.7-.48A6.985 6.985 0 0 1 1.5 10c0-.85.151-1.665.429-2.42a.75.75 0 0 1 .7-.58h2.564l4.033-3.796a.75.75 0 0 1 .811-.142Z" />
            <path d="M14.017 7.19a.75.75 0 0 1 1.044.193 4.004 4.004 0 0 1 0 4.435.75.75 0 1 1-1.237-.85 2.504 2.504 0 0 0 0-2.735.75.75 0 0 1 .193-1.044Z" />
            <path d="M15.807 4.882a.75.75 0 0 1 1.06-.04 8.02 8.02 0 0 1 0 11.12.75.75 0 0 1-1.1-1.02 6.52 6.52 0 0 0 0-9.06.75.75 0 0 1 .04-1Z" />
          </svg>
        )}
      </button>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={volume}
        onChange={handleSliderChange}
        className="w-20 h-1.5 accent-blue-500 cursor-pointer"
        title={`AI voice volume: ${Math.round(volume * 100)}%`}
        aria-label="AI voice volume"
      />
    </div>
  );
}

export default function SessionControls({
  isConnected,
  onStart,
  onEnd,
  metricsVisible,
  onToggleMetrics,
  transcriptVisible,
  onToggleTranscript,
  volume,
  onVolumeChange,
}: SessionControlsProps) {
  return (
    <div className="flex gap-2 items-center">
      {!isConnected ? (
        <button
          onClick={onStart}
          className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
        >
          Start Session
        </button>
      ) : (
        <>
          <MicToggle />
          <VolumeSlider volume={volume} onVolumeChange={onVolumeChange} />
          <button
            onClick={onEnd}
            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            End Session
          </button>
        </>
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
