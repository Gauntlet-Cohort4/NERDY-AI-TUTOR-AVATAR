"use client";

import { useMemo, useState } from "react";

interface ForceVectorProps {
  params: Record<string, unknown>;
}

interface Vector {
  magnitude: number;
  angle: number; // degrees from positive x-axis
  label?: string;
  color?: string;
}

export default function ForceVector({ params }: ForceVectorProps) {
  const vectors = Array.isArray(params.vectors) ? (params.vectors as Vector[]) : [];
  const title = typeof params.title === "string" ? params.title : "Force Vectors";
  const showResultant = params.show_resultant !== false;
  const scale = typeof params.scale === "number" ? params.scale : 1;

  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const width = 500;
  const height = 500;
  const cx = width / 2;
  const cy = height / 2;

  const DEFAULT_COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6"];

  const degToRad = (deg: number) => (deg * Math.PI) / 180;

  // Calculate resultant vector (memoized to avoid recomputation on hover)
  const { resultantMag, resultantAngle } = useMemo(() => {
    let rx = 0;
    let ry = 0;
    for (const v of vectors) {
      rx += v.magnitude * Math.cos(degToRad(v.angle));
      ry += v.magnitude * Math.sin(degToRad(v.angle));
    }
    return {
      resultantMag: Math.sqrt(rx * rx + ry * ry),
      resultantAngle: Math.atan2(ry, rx),
    };
  }, [vectors]);

  const maxMag = Math.max(
    ...vectors.map((v) => v.magnitude),
    showResultant ? resultantMag : 0,
    1
  );
  const arrowScale = (150 * scale) / maxMag;

  const renderArrow = (
    endX: number,
    endY: number,
    color: string,
    strokeWidth: number
  ) => {
    const angle = Math.atan2(endY - cy, endX - cx);
    const headLen = 12;
    const ax = endX - headLen * Math.cos(angle - 0.3);
    const ay = endY - headLen * Math.sin(angle - 0.3);
    const bx = endX - headLen * Math.cos(angle + 0.3);
    const by = endY - headLen * Math.sin(angle + 0.3);

    return (
      <>
        <line x1={cx} y1={cy} x2={endX} y2={endY} stroke={color} strokeWidth={strokeWidth} />
        <polygon points={`${endX},${endY} ${ax},${ay} ${bx},${by}`} fill={color} />
      </>
    );
  };

  return (
    <div className="flex flex-col items-center justify-center h-full p-6">
      <h3 className="text-lg font-semibold text-gray-200 mb-4">{title}</h3>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full max-w-lg"
        role="img"
        aria-label={title}
      >
        {/* Reference circle */}
        <circle cx={cx} cy={cy} r={160} fill="none" stroke="#374151" strokeWidth={0.5} strokeDasharray="4 4" />
        <circle cx={cx} cy={cy} r={80} fill="none" stroke="#374151" strokeWidth={0.5} strokeDasharray="4 4" />

        {/* Axis cross */}
        <line x1={cx - 180} y1={cy} x2={cx + 180} y2={cy} stroke="#4b5563" strokeWidth={0.5} />
        <line x1={cx} y1={cy - 180} x2={cx} y2={cy + 180} stroke="#4b5563" strokeWidth={0.5} />

        {/* Origin dot */}
        <circle cx={cx} cy={cy} r={4} fill="#6b7280" />

        {/* Vectors */}
        {vectors.map((v, i) => {
          const rad = degToRad(v.angle);
          const len = v.magnitude * arrowScale;
          // SVG y is inverted (positive angle goes up visually)
          const endX = cx + len * Math.cos(rad);
          const endY = cy - len * Math.sin(rad);
          const color = v.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length];
          const isHovered = hoveredIndex === i;

          return (
            <g
              key={`vec-${i}`}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
              className="cursor-pointer"
            >
              {renderArrow(endX, endY, color, isHovered ? 3 : 2)}
              <text
                x={endX + 8 * Math.cos(rad)}
                y={endY - 8 * Math.sin(rad)}
                fill={color}
                fontSize={isHovered ? 14 : 12}
                fontWeight={isHovered ? "bold" : "normal"}
              >
                {v.label || `F${i + 1}`}
              </text>
              {isHovered && (
                <text
                  x={endX + 8 * Math.cos(rad)}
                  y={endY - 8 * Math.sin(rad) + 16}
                  fill="#9ca3af"
                  fontSize={11}
                >
                  {v.magnitude.toFixed(1)}N @ {v.angle.toFixed(0)}&deg;
                </text>
              )}
            </g>
          );
        })}

        {/* Resultant */}
        {showResultant && vectors.length >= 2 && resultantMag > 0.01 && (
          <g>
            {renderArrow(
              cx + resultantMag * arrowScale * Math.cos(resultantAngle),
              cy - resultantMag * arrowScale * Math.sin(resultantAngle),
              "#fbbf24",
              2.5
            )}
            <text
              x={cx + resultantMag * arrowScale * Math.cos(resultantAngle) + 10}
              y={cy - resultantMag * arrowScale * Math.sin(resultantAngle)}
              fill="#fbbf24"
              fontSize={13}
              fontWeight="bold"
            >
              R = {resultantMag.toFixed(1)}N
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
