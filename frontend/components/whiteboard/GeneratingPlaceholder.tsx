"use client";

interface GeneratingPlaceholderProps {
  description?: string;
  title?: string;
}

export default function GeneratingPlaceholder({ description, title }: GeneratingPlaceholderProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      <div className="w-64 h-64 bg-gray-800 rounded-xl animate-pulse flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-400">{title || "Generating visual..."}</p>
        </div>
      </div>
      {description && (
        <p className="text-xs text-gray-500 mt-4 max-w-md text-center">{description}</p>
      )}
    </div>
  );
}
