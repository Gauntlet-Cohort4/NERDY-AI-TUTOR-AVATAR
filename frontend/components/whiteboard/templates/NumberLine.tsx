"use client";

import { useState } from "react";

interface NumberLineProps {
  params: Record<string, unknown>;
}

export default function NumberLine({ params }: NumberLineProps) {
  const min = typeof params.min === "number" ? params.min : 0;
  const max = typeof params.max === "number" ? params.max : 10;
  const markers = Array.isArray(params.markers)
    ? (params.markers as Array<{ value: number; label?: string; color?: string }>)
    : [];
  const title = typeof params.title === "string" ? params.title : "Number Line";
  const step = typeof params.step === "number" && params.step > 0 ? params.step : 1;

  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const width = 600;
  const height = 160;
  const padding = 60;
  const lineY = height / 2;
  const lineStart = padding;
  const lineEnd = width - padding;
  const lineLength = lineEnd - lineStart;
  const range = max - min;

  const toX = (value: number): number => {
    if (range === 0) return lineStart;
    return lineStart + ((value - min) / range) * lineLength;
  };

  // Generate tick values with safety limit to prevent infinite loops
  const MAX_TICKS = 200;
  const ticks: number[] = [];
  for (let v = min; v <= max && ticks.length < MAX_TICKS; v += step) {
    ticks.push(Math.round(v * 1000) / 1000);
  }

  return (
    <div className="flex flex-col items-center justify-center h-full p-6">
      <h3 className="text-lg font-semibold text-gray-200 mb-4">{title}</h3>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full max-w-2xl"
        role="img"
        aria-label={title}
      >
        {/* Main line */}
        <line
          x1={lineStart}
          y1={lineY}
          x2={lineEnd}
          y2={lineY}
          stroke="#9ca3af"
          strokeWidth={2}
        />

        {/* Arrowheads */}
        <polygon
          points={`${lineStart - 8},${lineY} ${lineStart + 2},${lineY - 5} ${lineStart + 2},${lineY + 5}`}
          fill="#9ca3af"
        />
        <polygon
          points={`${lineEnd + 8},${lineY} ${lineEnd - 2},${lineY - 5} ${lineEnd - 2},${lineY + 5}`}
          fill="#9ca3af"
        />

        {/* Tick marks */}
        {ticks.map((v) => {
          const x = toX(v);
          return (
            <g key={`tick-${v}`}>
              <line
                x1={x}
                y1={lineY - 8}
                x2={x}
                y2={lineY + 8}
                stroke="#6b7280"
                strokeWidth={1.5}
              />
              <text
                x={x}
                y={lineY + 24}
                textAnchor="middle"
                fill="#9ca3af"
                fontSize={12}
              >
                {v}
              </text>
            </g>
          );
        })}

        {/* Markers */}
        {markers.map((m, i) => {
          const x = toX(m.value);
          const color = m.color || "#3b82f6";
          const isHovered = hoveredIndex === i;
          return (
            <g
              key={`marker-${i}`}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
              className="cursor-pointer"
            >
              <circle
                cx={x}
                cy={lineY}
                r={isHovered ? 8 : 6}
                fill={color}
                stroke="white"
                strokeWidth={2}
                className="transition-all duration-200"
              />
              {(m.label || isHovered) && (
                <text
                  x={x}
                  y={lineY - 16}
                  textAnchor="middle"
                  fill={color}
                  fontSize={isHovered ? 14 : 12}
                  fontWeight={isHovered ? "bold" : "normal"}
                >
                  {m.label || String(m.value)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
