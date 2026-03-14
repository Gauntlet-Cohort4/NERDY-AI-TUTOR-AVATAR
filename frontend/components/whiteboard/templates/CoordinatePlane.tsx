"use client";

import { useState } from "react";

interface CoordinatePlaneProps {
  params: Record<string, unknown>;
}

interface Point {
  x: number;
  y: number;
  label?: string;
  color?: string;
}

interface Line {
  slope: number;
  intercept: number;
  color?: string;
  label?: string;
}

export default function CoordinatePlane({ params }: CoordinatePlaneProps) {
  const xMin = typeof params.x_min === "number" ? params.x_min : -10;
  const xMax = typeof params.x_max === "number" ? params.x_max : 10;
  const yMin = typeof params.y_min === "number" ? params.y_min : -10;
  const yMax = typeof params.y_max === "number" ? params.y_max : 10;
  const title = typeof params.title === "string" ? params.title : "Coordinate Plane";
  const points = Array.isArray(params.points) ? (params.points as Point[]) : [];
  const lines = Array.isArray(params.lines) ? (params.lines as Line[]) : [];

  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null);

  const width = 500;
  const height = 500;
  const padding = 50;
  const plotW = width - 2 * padding;
  const plotH = height - 2 * padding;

  const toSvgX = (x: number) => padding + ((x - xMin) / (xMax - xMin)) * plotW;
  const toSvgY = (y: number) => padding + ((yMax - y) / (yMax - yMin)) * plotH;

  // Grid lines
  const gridLinesX: number[] = [];
  for (let x = Math.ceil(xMin); x <= Math.floor(xMax); x++) gridLinesX.push(x);
  const gridLinesY: number[] = [];
  for (let y = Math.ceil(yMin); y <= Math.floor(yMax); y++) gridLinesY.push(y);

  return (
    <div className="flex flex-col items-center justify-center h-full p-6">
      <h3 className="text-lg font-semibold text-gray-200 mb-4">{title}</h3>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full max-w-lg"
        role="img"
        aria-label={title}
      >
        {/* Clip path for lines — must precede elements that reference it */}
        <defs>
          <clipPath id="plot-clip">
            <rect x={padding} y={padding} width={plotW} height={plotH} />
          </clipPath>
        </defs>

        {/* Grid */}
        {gridLinesX.map((x) => (
          <line
            key={`gx-${x}`}
            x1={toSvgX(x)}
            y1={padding}
            x2={toSvgX(x)}
            y2={height - padding}
            stroke={x === 0 ? "#6b7280" : "#374151"}
            strokeWidth={x === 0 ? 2 : 0.5}
          />
        ))}
        {gridLinesY.map((y) => (
          <line
            key={`gy-${y}`}
            x1={padding}
            y1={toSvgY(y)}
            x2={width - padding}
            y2={toSvgY(y)}
            stroke={y === 0 ? "#6b7280" : "#374151"}
            strokeWidth={y === 0 ? 2 : 0.5}
          />
        ))}

        {/* Axis labels */}
        <text x={width - padding + 10} y={toSvgY(0) + 4} fill="#9ca3af" fontSize={14}>x</text>
        <text x={toSvgX(0) - 14} y={padding - 10} fill="#9ca3af" fontSize={14}>y</text>

        {/* Tick labels — every other integer to avoid clutter */}
        {gridLinesX.filter((x) => x !== 0 && x % 2 === 0).map((x) => (
          <text key={`lx-${x}`} x={toSvgX(x)} y={toSvgY(0) + 18} textAnchor="middle" fill="#6b7280" fontSize={10}>
            {x}
          </text>
        ))}
        {gridLinesY.filter((y) => y !== 0 && y % 2 === 0).map((y) => (
          <text key={`ly-${y}`} x={toSvgX(0) - 14} y={toSvgY(y) + 4} textAnchor="end" fill="#6b7280" fontSize={10}>
            {y}
          </text>
        ))}

        {/* Lines (y = mx + b) */}
        {lines.map((line, i) => {
          const x1 = xMin;
          const y1 = line.slope * x1 + line.intercept;
          const x2 = xMax;
          const y2 = line.slope * x2 + line.intercept;
          const color = line.color || "#60a5fa";
          return (
            <g key={`line-${i}`}>
              <line
                x1={toSvgX(x1)}
                y1={toSvgY(y1)}
                x2={toSvgX(x2)}
                y2={toSvgY(y2)}
                stroke={color}
                strokeWidth={2}
                clipPath="url(#plot-clip)"
              />
              {line.label && (
                <text x={toSvgX(x2) - 10} y={toSvgY(y2) - 8} fill={color} fontSize={11}>
                  {line.label}
                </text>
              )}
            </g>
          );
        })}

        {/* Points */}
        {points.map((pt, i) => {
          const color = pt.color || "#f59e0b";
          const isHovered = hoveredPoint === i;
          return (
            <g
              key={`pt-${i}`}
              onMouseEnter={() => setHoveredPoint(i)}
              onMouseLeave={() => setHoveredPoint(null)}
              className="cursor-pointer"
            >
              <circle
                cx={toSvgX(pt.x)}
                cy={toSvgY(pt.y)}
                r={isHovered ? 7 : 5}
                fill={color}
                stroke="white"
                strokeWidth={1.5}
              />
              {(pt.label || isHovered) && (
                <text
                  x={toSvgX(pt.x) + 10}
                  y={toSvgY(pt.y) - 8}
                  fill={color}
                  fontSize={isHovered ? 13 : 11}
                  fontWeight={isHovered ? "bold" : "normal"}
                >
                  {pt.label || `(${pt.x}, ${pt.y})`}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
