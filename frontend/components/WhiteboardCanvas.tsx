"use client";

import type { WhiteboardPayload } from "@/lib/types";
import EquationRenderer from "./whiteboard/EquationRenderer";
import DiagramViewer from "./whiteboard/DiagramViewer";
import InteractiveTemplate from "./whiteboard/InteractiveTemplate";
import GeneratingPlaceholder from "./whiteboard/GeneratingPlaceholder";

interface WhiteboardCanvasProps {
  payload: WhiteboardPayload | null;
}

export default function WhiteboardCanvas({ payload }: WhiteboardCanvasProps) {
  if (!payload) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <p className="text-sm">Whiteboard will appear here when the tutor shows visuals</p>
      </div>
    );
  }

  switch (payload.type) {
    case "equation":
      return <EquationRenderer latex={payload.latex || ""} title={payload.title} />;
    case "image":
    case "svg_diagram":
      return (
        <DiagramViewer
          content={payload.content || ""}
          title={payload.title}
          altText={payload.alt_text}
          type={payload.type}
        />
      );
    case "interactive":
      return (
        <InteractiveTemplate
          templateId={payload.template_id || ""}
          params={payload.params || {}}
        />
      );
    case "generating":
      return <GeneratingPlaceholder description={payload.description} title={payload.title} />;
    default:
      return null;
  }
}
