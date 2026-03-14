"use client";

import NumberLine from "./templates/NumberLine";
import CoordinatePlane from "./templates/CoordinatePlane";
import FractionBars from "./templates/FractionBars";
import ForceVector from "./templates/ForceVector";
import PeriodicTableSection from "./templates/PeriodicTableSection";

interface InteractiveTemplateProps {
  templateId: string;
  params: Record<string, unknown>;
}

const TEMPLATE_MAP: Record<string, React.ComponentType<{ params: Record<string, unknown> }>> = {
  number_line: NumberLine,
  coordinate_plane: CoordinatePlane,
  fraction_bars: FractionBars,
  force_vector: ForceVector,
  periodic_table_section: PeriodicTableSection,
};

export default function InteractiveTemplate({ templateId, params }: InteractiveTemplateProps) {
  const Component = TEMPLATE_MAP[templateId];

  if (!Component) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <p>Unknown template: {templateId}</p>
      </div>
    );
  }

  return <Component params={params} />;
}
