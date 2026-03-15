"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import DOMPurify from "dompurify";

interface DiagramViewerProps {
  content: string;
  title?: string;
  altText?: string;
  type: "image" | "svg_diagram";
}

export default function DiagramViewer({ content, title, altText, type }: DiagramViewerProps) {
  const [zoomed, setZoomed] = useState(false);

  const safeSvg = useMemo(() => {
    if (type !== "svg_diagram") return "";
    return DOMPurify.sanitize(content, {
      USE_PROFILES: { svg: true, svgFilters: true },
      FORBID_TAGS: ["script"],
      FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover"],
    });
  }, [content, type]);

  const handleToggleZoom = () => setZoomed((prev) => !prev);
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleToggleZoom();
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full p-6">
      {title && <h3 className="text-lg font-semibold text-gray-200 mb-4">{title}</h3>}
      <div
        className={`transition-transform duration-300 cursor-pointer ${zoomed ? "scale-150" : ""}`}
        onClick={handleToggleZoom}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-label={zoomed ? "Click to zoom out" : "Click to zoom in"}
      >
        {type === "svg_diagram" ? (
          <div
            className="max-w-2xl max-h-96"
            dangerouslySetInnerHTML={{ __html: safeSvg }}
          />
        ) : (
          <Image
            src={content}
            alt={altText || title || "Educational diagram"}
            width={672}
            height={384}
            className="max-w-2xl max-h-96 rounded-lg object-contain"
            unoptimized
          />
        )}
      </div>
      <p className="text-xs text-gray-500 mt-3">{altText || "Click to zoom"}</p>
    </div>
  );
}
