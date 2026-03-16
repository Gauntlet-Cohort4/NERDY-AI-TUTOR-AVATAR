"use client";

import { useEffect, useRef } from "react";

interface EquationRendererProps {
  latex: string;
  title?: string;
}

const MAX_LATEX_LENGTH = 2000;

export default function EquationRenderer({ latex, title }: EquationRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !latex) return;

    if (latex.length > MAX_LATEX_LENGTH) {
      if (containerRef.current) {
        containerRef.current.textContent = "Error: LaTeX expression too long to render.";
      }
      return;
    }

    // Dynamic import katex to avoid SSR issues
    import("katex")
      .then((katex) => {
        if (containerRef.current) {
          katex.default.render(latex, containerRef.current, {
            throwOnError: false,
            displayMode: true,
            output: "html",
          });
        }
      })
      .catch(() => {
        // Fallback to raw LaTeX string if katex fails to load
        if (containerRef.current) {
          containerRef.current.textContent = latex;
        }
      });
  }, [latex]);

  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      {title && <h3 className="text-lg font-semibold text-gray-200 mb-6">{title}</h3>}
      <div
        ref={containerRef}
        className="text-3xl text-white bg-gray-800/50 rounded-xl p-8 max-w-4xl w-full"
      />
    </div>
  );
}
