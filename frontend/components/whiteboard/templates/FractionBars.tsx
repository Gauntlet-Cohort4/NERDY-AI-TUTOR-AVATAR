"use client";

import { useState } from "react";

interface FractionBarsProps {
  params: Record<string, unknown>;
}

interface Fraction {
  numerator: number;
  denominator: number;
  color?: string;
  label?: string;
}

export default function FractionBars({ params }: FractionBarsProps) {
  const fractions = Array.isArray(params.fractions) ? (params.fractions as Fraction[]) : [];
  const title = typeof params.title === "string" ? params.title : "Fraction Bars";
  const showEquivalent = params.show_equivalent === true;

  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const width = 600;
  const barHeight = 50;
  const barGap = 24;
  const paddingX = 60;
  const paddingY = 50;
  const barWidth = width - 2 * paddingX;
  const height = paddingY + fractions.length * (barHeight + barGap) + 40;

  const DEFAULT_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

  return (
    <div className="flex flex-col items-center justify-center h-full p-6">
      <h3 className="text-lg font-semibold text-gray-200 mb-4">{title}</h3>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full max-w-2xl"
        role="img"
        aria-label={title}
      >
        {fractions.map((frac, i) => {
          const y = paddingY + i * (barHeight + barGap);
          const color = frac.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length];
          const isHovered = hoveredIndex === i;
          const denom = Math.max(frac.denominator, 1);
          const numer = Math.min(frac.numerator, denom);
          const segmentWidth = barWidth / denom;
          const filledSegments = numer;

          return (
            <g
              key={`frac-${i}`}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
              className="cursor-pointer"
            >
              {/* Label */}
              <text
                x={paddingX - 10}
                y={y + barHeight / 2 + 5}
                textAnchor="end"
                fill={isHovered ? "white" : "#d1d5db"}
                fontSize={isHovered ? 16 : 14}
                fontWeight={isHovered ? "bold" : "normal"}
              >
                {frac.label || `${frac.numerator}/${frac.denominator}`}
              </text>

              {/* Background bar */}
              <rect
                x={paddingX}
                y={y}
                width={barWidth}
                height={barHeight}
                rx={6}
                fill="#1f2937"
                stroke="#374151"
                strokeWidth={1}
              />

              {/* Filled segments */}
              {Array.from({ length: filledSegments }).map((_, si) => (
                <rect
                  key={`seg-${si}`}
                  x={paddingX + si * segmentWidth + 1}
                  y={y + 1}
                  width={segmentWidth - 2}
                  height={barHeight - 2}
                  rx={si === 0 ? 5 : 0}
                  fill={color}
                  opacity={isHovered ? 1 : 0.8}
                />
              ))}

              {/* Segment dividers */}
              {Array.from({ length: denom - 1 }).map((_, di) => (
                <line
                  key={`div-${di}`}
                  x1={paddingX + (di + 1) * segmentWidth}
                  y1={y}
                  x2={paddingX + (di + 1) * segmentWidth}
                  y2={y + barHeight}
                  stroke="#4b5563"
                  strokeWidth={1}
                />
              ))}

              {/* Hover tooltip showing decimal */}
              {isHovered && (
                <text
                  x={paddingX + barWidth + 10}
                  y={y + barHeight / 2 + 5}
                  fill="#9ca3af"
                  fontSize={12}
                >
                  = {(numer / denom).toFixed(3)}
                </text>
              )}
            </g>
          );
        })}

        {/* Equivalence indicator */}
        {showEquivalent && fractions.length >= 2 && (
          <text
            x={width / 2}
            y={height - 10}
            textAnchor="middle"
            fill="#60a5fa"
            fontSize={14}
            fontWeight="bold"
          >
            These fractions are equivalent
          </text>
        )}
      </svg>
    </div>
  );
}
