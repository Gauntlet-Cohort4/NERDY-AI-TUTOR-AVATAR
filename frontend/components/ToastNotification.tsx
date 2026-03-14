"use client";

import { useEffect } from "react";

export interface Toast {
  readonly id: string;
  readonly message: string;
  readonly type: "success" | "info" | "error";
}

interface ToastNotificationProps {
  readonly toasts: readonly Toast[];
  readonly onDismiss: (id: string) => void;
}

export default function ToastNotification({
  toasts,
  onDismiss,
}: ToastNotificationProps) {
  return (
    <div className="fixed bottom-6 left-6 z-50 flex flex-col gap-2" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  readonly toast: Toast;
  readonly onDismiss: (id: string) => void;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 5000);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  const bgColor =
    toast.type === "success"
      ? "bg-green-800/90"
      : toast.type === "error"
        ? "bg-red-800/90"
        : "bg-blue-800/90";

  const borderColor =
    toast.type === "success"
      ? "border-green-600"
      : toast.type === "error"
        ? "border-red-600"
        : "border-blue-600";

  return (
    <div
      className={`${bgColor} ${borderColor} border rounded-lg px-4 py-3 text-sm text-white shadow-lg animate-slide-in max-w-sm`}
    >
      <div className="flex items-center justify-between gap-3">
        <span>{toast.message}</span>
        <button
          onClick={() => onDismiss(toast.id)}
          aria-label="Dismiss notification"
          className="text-white/60 hover:text-white text-lg"
        >
          &times;
        </button>
      </div>
    </div>
  );
}
