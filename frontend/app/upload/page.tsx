"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createLogger } from "@/lib/logger";
import { getUserId } from "@/lib/user";
import { uploadFile, getUpload } from "@/lib/api";
import ToastNotification from "@/components/ToastNotification";
import type { Toast } from "@/components/ToastNotification";
import type { Upload, UploadStatus } from "@/lib/types";

const logger = createLogger("UploadPage");

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const ACCEPTED_TYPES = ["application/pdf", "image/png", "image/jpeg", "image/jpg"];
const ACCEPTED_EXTENSIONS = ".pdf,.png,.jpg,.jpeg";
const POLL_INTERVAL_MS = 2000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// NOTE: Client-side MIME type validation is based on the browser-reported type,
// which can be spoofed. Server-side magic-byte validation is the real gate and
// should reject files whose content does not match the claimed type.
function isValidFileType(file: File): boolean {
  return ACCEPTED_TYPES.includes(file.type);
}

function isValidFileSize(file: File): boolean {
  return file.size <= MAX_FILE_SIZE_BYTES;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusLabel(status: UploadStatus): string {
  switch (status) {
    case "uploaded":
      return "Uploaded — waiting for processing...";
    case "processing":
      return "Analyzing your worksheet...";
    case "classified":
      return "Classification complete!";
    case "reviewing":
      return "Review in progress";
    default:
      return "Unknown status";
  }
}

function statusColor(status: UploadStatus): string {
  switch (status) {
    case "uploaded":
    case "processing":
      return "#FFC107";
    case "classified":
      return "#28A745";
    case "reviewing":
      return "#007AFF";
    default:
      return "#6a7f99";
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function UploadDropZone({
  onFileDrop,
  isDragging,
  onDragEnter,
  onDragLeave,
  onDragOver,
  onDrop,
  uploading,
  inputRef,
}: {
  readonly onFileDrop: (file: File) => void;
  readonly isDragging: boolean;
  readonly onDragEnter: (e: React.DragEvent) => void;
  readonly onDragLeave: (e: React.DragEvent) => void;
  readonly onDragOver: (e: React.DragEvent) => void;
  readonly onDrop: (e: React.DragEvent) => void;
  readonly uploading: boolean;
  readonly inputRef: React.RefObject<HTMLInputElement>;
}) {
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onDrop(e);
      const file = e.dataTransfer.files[0];
      if (file) onFileDrop(file);
    },
    [onFileDrop, onDrop],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileDrop(file);
    },
    [onFileDrop],
  );

  const handleClick = useCallback(() => {
    inputRef.current?.click();
  }, [inputRef]);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload worksheet file. Drag and drop or click to browse."
      className="relative flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer"
      style={{
        borderColor: isDragging ? "#007AFF" : "rgba(255,255,255,0.12)",
        background: isDragging ? "rgba(0,122,255,0.06)" : "rgba(255,255,255,0.03)",
        padding: "60px 40px",
        minHeight: 240,
      }}
      onDrop={handleDrop}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") handleClick();
      }}
    >
      <svg
        aria-hidden="true"
        width="48"
        height="48"
        viewBox="0 0 24 24"
        fill="none"
        stroke={isDragging ? "#007AFF" : "#6a7f99"}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>

      <div className="text-center">
        <p className="text-white font-semibold text-base mb-1">
          {uploading ? "Uploading..." : "Drop your worksheet here"}
        </p>
        <p className="text-sm" style={{ color: "#6a7f99" }}>
          or click to browse — PDF, PNG, JPG up to 10 MB
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        className="hidden"
        onChange={handleInputChange}
        aria-label="File input"
      />
    </div>
  );
}

function ClassificationDisplay({
  upload,
  onStartReview,
}: {
  readonly upload: Upload;
  readonly onStartReview: () => void;
}) {
  const subjectLabel = upload.detected_subject
    ? upload.detected_subject.replace(/_/g, " ")
    : "Unknown";
  const gradeLabel = upload.detected_grade ? `Grade ${upload.detected_grade}` : "Unknown";

  return (
    <div
      className="rounded-2xl border p-6"
      style={{
        background: "rgba(255,255,255,0.03)",
        borderColor: "rgba(255,255,255,0.08)",
      }}
    >
      <div className="flex items-center gap-3 mb-4">
        <div
          className="w-3 h-3 rounded-full"
          style={{ background: statusColor(upload.status) }}
        />
        <span className="text-sm font-medium" style={{ color: statusColor(upload.status) }}>
          {statusLabel(upload.status)}
        </span>
      </div>

      <div className="flex gap-3 mb-4 flex-wrap">
        <span className="px-3 py-1.5 rounded-full text-xs font-semibold bg-blue-900/40 text-blue-300 border border-blue-700/50 capitalize">
          {subjectLabel}
        </span>
        <span className="px-3 py-1.5 rounded-full text-xs font-semibold bg-purple-900/40 text-purple-300 border border-purple-700/50">
          {gradeLabel}
        </span>
      </div>

      <p className="text-sm text-gray-400 mb-2">
        File: {upload.file_name}
      </p>

      {upload.status === "classified" && (
        <button
          onClick={onStartReview}
          className="mt-4 text-white border-none cursor-pointer font-semibold inline-flex items-center gap-2 transition-all duration-300 hover:-translate-y-0.5 rounded-xl px-6 py-3 text-sm"
          style={{
            background: "linear-gradient(135deg, #007AFF, #0056b3)",
            fontFamily: "inherit",
            boxShadow: "0 8px 32px rgba(0,122,255,0.3)",
          }}
        >
          Start Review Chat
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function UploadPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [upload, setUpload] = useState<Upload | null>(null);
  const [toasts, setToasts] = useState<readonly Toast[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const dragCounter = useRef(0);
  const [userId, setUserId] = useState<string | null>(null);
  useEffect(() => {
    setUserId(getUserId());
  }, []);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const addToast = useCallback((message: string, type: Toast["type"]) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const startPolling = useCallback(
    (uploadId: string) => {
      if (pollRef.current) clearInterval(pollRef.current);

      pollRef.current = setInterval(async () => {
        try {
          const updated = await getUpload(uploadId);
          if (
            typeof updated === "object" &&
            updated !== null &&
            typeof updated.id === "string" &&
            typeof updated.status === "string"
          ) {
            setUpload(updated);
            if (updated.status !== "uploaded" && updated.status !== "processing") {
              if (pollRef.current) clearInterval(pollRef.current);
              pollRef.current = null;
              if (updated.status === "classified") {
                addToast("Worksheet classified successfully!", "success");
              }
            }
          }
        } catch (err) {
          logger.error("poll_upload_failed", { uploadId, error: String(err) });
        }
      }, POLL_INTERVAL_MS);
    },
    [addToast],
  );

  const handleFileDrop = useCallback(
    async (file: File) => {
      if (!userId) {
        addToast("Please start a tutoring session first to get a user ID.", "error");
        return;
      }

      if (!isValidFileType(file)) {
        addToast("Invalid file type. Please upload a PDF, PNG, or JPG file.", "error");
        return;
      }

      if (!isValidFileSize(file)) {
        addToast(
          `File too large (${formatFileSize(file.size)}). Maximum size is 10 MB.`,
          "error",
        );
        return;
      }

      logger.info("upload_started", { fileName: file.name, size: file.size });
      setUploading(true);
      setUpload(null);

      try {
        const result = await uploadFile(userId, file);
        if (
          typeof result === "object" &&
          result !== null &&
          typeof result.id === "string"
        ) {
          setUpload(result);
          addToast("File uploaded! Processing...", "info");
          startPolling(result.id);
        } else {
          addToast("Unexpected response from server.", "error");
          logger.error("upload_invalid_response", { result: String(result) });
        }
      } catch (err) {
        logger.error("upload_failed", { error: String(err) });
        addToast("Upload failed. Please try again.", "error");
      } finally {
        setUploading(false);
      }
    },
    [userId, addToast, startPolling],
  );

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    dragCounter.current = 0;
    setIsDragging(false);
  }, []);

  const handleStartReview = useCallback(() => {
    if (upload) {
      router.push(`/review/${upload.id}`);
    }
  }, [upload, router]);

  if (!userId) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center" style={{ background: "#0a1d37" }}>
        <div className="text-center max-w-md px-6">
          <svg
            aria-hidden="true"
            className="mx-auto mb-4"
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#6a7f99"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <h2 className="text-white text-xl font-bold mb-2">Session Required</h2>
          <p className="text-sm mb-6" style={{ color: "#6a7f99" }}>
            Start a tutoring session first so we can associate your uploads with your account.
          </p>
          <button
            onClick={() => router.push("/")}
            className="text-white border-none cursor-pointer font-semibold rounded-xl px-6 py-3 text-sm transition-all duration-300 hover:-translate-y-0.5"
            style={{
              background: "linear-gradient(135deg, #007AFF, #0056b3)",
              fontFamily: "inherit",
            }}
          >
            Go to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "#0a1d37" }}>
      {/* Header */}
      <nav
        className="sticky top-0 z-50 flex items-center justify-between px-10 py-4"
        style={{
          background: "rgba(10,29,55,0.95)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-2.5 bg-transparent border-none cursor-pointer"
          aria-label="Go to home page"
        >
          <div
            className="flex items-center justify-center w-9 h-9 rounded-[10px] text-white text-base font-extrabold"
            style={{ background: "linear-gradient(135deg, #007AFF, #0056b3)" }}
          >
            N
          </div>
          <span className="text-white font-bold text-lg" style={{ letterSpacing: "-0.02em" }}>
            Nerdy AI Tutor
          </span>
        </button>
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/flash-cards")}
            className="text-white/70 text-sm font-medium px-4 py-2 rounded-lg hover:text-white hover:bg-white/5 transition-colors bg-transparent border-none cursor-pointer"
            style={{ fontFamily: "inherit" }}
          >
            Flash Cards
          </button>
        </div>
      </nav>

      {/* Content */}
      <div className="mx-auto px-6 py-12" style={{ maxWidth: 640 }}>
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-1.5 bg-transparent border-none cursor-pointer text-blue-400 text-sm hover:text-blue-300 mb-6"
          style={{ fontFamily: "inherit" }}
        >
          <span>&larr;</span> Back to Dashboard
        </button>
        <h1 className="text-white text-2xl font-bold mb-2 text-center">
          Upload Worksheet
        </h1>
        <p className="text-center text-sm mb-8" style={{ color: "#6a7f99" }}>
          Upload a worksheet or assignment to get AI-powered review feedback.
        </p>

        <UploadDropZone
          onFileDrop={handleFileDrop}
          isDragging={isDragging}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          uploading={uploading}
          inputRef={inputRef}
        />

        {/* Upload progress spinner */}
        {uploading && (
          <div className="flex items-center justify-center gap-3 mt-6">
            <div
              className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: "#007AFF", borderTopColor: "transparent" }}
            />
            <span className="text-sm" style={{ color: "#6a7f99" }}>
              Uploading file...
            </span>
          </div>
        )}

        {/* Processing state */}
        {upload && (upload.status === "uploaded" || upload.status === "processing") && (
          <div className="flex items-center justify-center gap-3 mt-6">
            <div
              className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: "#FFC107", borderTopColor: "transparent" }}
            />
            <span className="text-sm" style={{ color: "#FFC107" }}>
              {statusLabel(upload.status)}
            </span>
          </div>
        )}

        {/* Classification results */}
        {upload && (upload.status === "classified" || upload.status === "reviewing") && (
          <div className="mt-8">
            <ClassificationDisplay upload={upload} onStartReview={handleStartReview} />
          </div>
        )}
      </div>

      <ToastNotification toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
