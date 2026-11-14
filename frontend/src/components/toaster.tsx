"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { useToasts, type Toast } from "@/lib/toast";

const ICON = {
  success: <CheckCircle2 className="size-4 text-signal" />,
  error: <AlertCircle className="size-4 text-danger" />,
  info: <Info className="size-4 text-fg-2" />,
};

function ToastItem({ t }: { t: Toast }) {
  const dismiss = useToasts((s) => s.dismiss);
  const [leaving, setLeaving] = useState(false);
  const [paused, setPaused] = useState(false);
  const remaining = useRef(t.duration);

  // Auto-dismiss, paused while hovered or focused so the message can be read or acted on.
  useEffect(() => {
    if (paused || leaving) return;
    const started = Date.now();
    const timer = setTimeout(() => setLeaving(true), remaining.current);
    return () => {
      clearTimeout(timer);
      remaining.current -= Date.now() - started;
    };
  }, [paused, leaving]);

  useEffect(() => {
    if (!leaving) return;
    const timer = setTimeout(() => dismiss(t.id), 180);
    return () => clearTimeout(timer);
  }, [leaving, dismiss, t.id]);

  return (
    <li
      role={t.kind === "error" ? "alert" : "status"}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      className={`pointer-events-auto flex w-full items-start gap-3 rounded-[12px] border border-line-strong bg-canvas px-4 py-3 shadow-[0_8px_30px_rgb(0_0_0/0.14)] ${
        leaving ? "toast-out" : "toast-in"
      }`}
    >
      <span className="mt-[3px] shrink-0">{ICON[t.kind]}</span>
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium leading-5 text-fg">{t.title}</p>
        {t.description && <p className="mt-0.5 break-words text-[12px] leading-[18px] text-fg-2">{t.description}</p>}
        {t.action && (
          <button
            onClick={() => {
              t.action!.onClick();
              setLeaving(true);
            }}
            className="mt-2 rounded-md border border-line-strong px-2.5 py-1 text-[12px] text-fg transition-colors hover:bg-surface-2"
          >
            {t.action.label}
          </button>
        )}
      </div>
      <button
        onClick={() => setLeaving(true)}
        className="-mr-1 shrink-0 rounded p-1 text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg"
        aria-label="Dismiss notification"
      >
        <X className="size-3.5" />
      </button>
    </li>
  );
}

/** Mounted once in the root layout. Bottom-right on desktop, bottom-center on phones. */
export default function Toaster() {
  const toasts = useToasts((s) => s.toasts);
  return (
    <ol
      aria-live="polite"
      aria-label="Notifications"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-[100] flex flex-col items-center gap-2 p-4 sm:inset-x-auto sm:right-0 sm:w-[380px] sm:items-end"
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} t={t} />
      ))}
    </ol>
  );
}
