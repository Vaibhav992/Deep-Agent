"use client";

import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";

/**
 * Modal confirmation built on the native <dialog>: the browser provides the focus trap,
 * Escape-to-close, the backdrop and inert background for free.
 */
export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  destructive = false,
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description?: React.ReactNode;
  confirmLabel?: string;
  destructive?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      d.showModal();
      cancelRef.current?.focus(); // Safe default for a destructive action.
    } else if (!open && d.open) {
      d.close();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault(); // Escape: route through onCancel so parent state stays in sync.
        if (!busy) onCancel();
      }}
      onClick={(e) => {
        if (e.target === ref.current && !busy) onCancel(); // Click on the backdrop.
      }}
      aria-labelledby="confirm-title"
      className="dialog-in m-auto w-[calc(100%-32px)] max-w-[400px] rounded-[16px] border border-line-strong bg-canvas p-0 text-fg shadow-[0_24px_60px_rgb(0_0_0/0.25)] backdrop:bg-black/50"
    >
      <div className="p-5">
        <h2 id="confirm-title" className="text-[15px] font-medium leading-6">{title}</h2>
        {description && <div className="mt-1.5 text-[13px] leading-5 text-fg-2">{description}</div>}
      </div>
      <div className="flex justify-end gap-2 border-t border-line px-5 py-3">
        <button
          ref={cancelRef}
          onClick={onCancel}
          disabled={busy}
          className="rounded-full border border-line-strong px-4 py-1.5 text-[13px] text-fg transition-colors hover:bg-surface-2 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          disabled={busy}
          className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-[13px] transition-opacity hover:opacity-90 disabled:opacity-70 ${
            destructive ? "bg-danger text-on-ink" : "bg-ink text-on-ink"
          }`}
        >
          {busy && <Loader2 className="size-3.5 animate-spin" />}
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
