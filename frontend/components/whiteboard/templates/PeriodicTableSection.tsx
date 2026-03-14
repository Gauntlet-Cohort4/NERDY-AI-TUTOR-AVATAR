"use client";

import { useState } from "react";

interface PeriodicTableSectionProps {
  params: Record<string, unknown>;
}

interface ElementData {
  symbol: string;
  name: string;
  atomic_number: number;
  atomic_mass?: number;
  group?: string;
  color?: string;
  highlighted?: boolean;
}

const DEFAULT_ELEMENT_COLOR: Record<string, string> = {
  "alkali metal": "#dc2626",
  "alkaline earth metal": "#ea580c",
  "transition metal": "#d97706",
  metalloid: "#65a30d",
  nonmetal: "#0d9488",
  "noble gas": "#7c3aed",
  halogen: "#2563eb",
  "post-transition metal": "#64748b",
};

export default function PeriodicTableSection({ params }: PeriodicTableSectionProps) {
  const elements = Array.isArray(params.elements) ? (params.elements as ElementData[]) : [];
  const title = typeof params.title === "string" ? params.title : "Periodic Table";
  const columns = typeof params.columns === "number" ? params.columns : Math.min(elements.length, 6);

  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const cellSize = 80;
  const cellGap = 6;
  const paddingX = 30;
  const paddingY = 50;
  const rows = Math.ceil(elements.length / columns);
  const width = paddingX * 2 + columns * (cellSize + cellGap);
  const height = paddingY + rows * (cellSize + cellGap) + 60;

  return (
    <div className="flex flex-col items-center justify-center h-full p-6">
      <h3 className="text-lg font-semibold text-gray-200 mb-4">{title}</h3>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full max-w-3xl"
        role="img"
        aria-label={title}
      >
        {elements.map((el, i) => {
          const col = i % columns;
          const row = Math.floor(i / columns);
          const x = paddingX + col * (cellSize + cellGap);
          const y = paddingY + row * (cellSize + cellGap);
          const isHovered = hoveredIndex === i;
          const isHighlighted = el.highlighted === true;

          const baseColor =
            el.color ||
            (el.group ? DEFAULT_ELEMENT_COLOR[el.group.toLowerCase()] : undefined) ||
            "#6b7280";

          return (
            <g
              key={`el-${i}`}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
              className="cursor-pointer"
            >
              {/* Cell background */}
              <rect
                x={x}
                y={y}
                width={cellSize}
                height={cellSize}
                rx={6}
                fill={isHighlighted ? baseColor : "#1f2937"}
                opacity={isHovered ? 1 : isHighlighted ? 0.7 : 0.3}
                stroke={isHovered ? "white" : isHighlighted ? baseColor : "#374151"}
                strokeWidth={isHovered ? 2 : 1}
              />

              {/* Atomic number */}
              <text
                x={x + 8}
                y={y + 16}
                fill={isHighlighted ? "white" : "#6b7280"}
                fontSize={10}
              >
                {el.atomic_number}
              </text>

              {/* Symbol */}
              <text
                x={x + cellSize / 2}
                y={y + cellSize / 2 + 4}
                textAnchor="middle"
                fill="white"
                fontSize={isHovered ? 22 : 20}
                fontWeight="bold"
              >
                {el.symbol}
              </text>

              {/* Name */}
              <text
                x={x + cellSize / 2}
                y={y + cellSize - 12}
                textAnchor="middle"
                fill={isHighlighted ? "rgba(255,255,255,0.8)" : "#6b7280"}
                fontSize={8}
              >
                {el.name}
              </text>

              {/* Atomic mass (on hover) */}
              {isHovered && el.atomic_mass && (
                <text
                  x={x + cellSize / 2}
                  y={y + cellSize + 14}
                  textAnchor="middle"
                  fill="#9ca3af"
                  fontSize={10}
                >
                  {el.atomic_mass.toFixed(2)} u
                </text>
              )}
            </g>
          );
        })}

        {/* Legend for groups if present */}
        {hoveredIndex !== null && elements[hoveredIndex]?.group && (
          <text
            x={width / 2}
            y={height - 10}
            textAnchor="middle"
            fill="#9ca3af"
            fontSize={12}
          >
            Group: {elements[hoveredIndex].group}
          </text>
        )}
      </svg>
    </div>
  );
}
