"use client";

import { create } from "zustand";

export type ToastKind = "success" | "error" | "info";

export interface Toast {
  id: number;
  kind: ToastKind;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  /** ms before auto-dismiss; errors stay longer so they can be read. */
  duration: number;
}

type ToastInput = Omit<Toast, "id" | "kind" | "duration"> & { duration?: number };

interface ToastState {
  toasts: Toast[];
  push: (kind: ToastKind, input: ToastInput) => number;
  dismiss: (id: number) => void;
}

const MAX_VISIBLE = 4;
const DEFAULT_MS: Record<ToastKind, number> = { success: 3500, info: 4500, error: 7000 };
let nextId = 1;

export const useToasts = create<ToastState>((set) => ({
  toasts: [],
  push: (kind, input) => {
    const id = nextId++;
    const t: Toast = { id, kind, duration: input.duration ?? DEFAULT_MS[kind], ...input };
    // Newest last; drop the oldest when the stack is full.
    set((s) => ({ toasts: [...s.toasts, t].slice(-MAX_VISIBLE) }));
    return id;
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Fire-and-forget notifications, callable from anywhere on the client. */
export const toast = {
  success: (title: string, opts: Omit<ToastInput, "title"> = {}) => useToasts.getState().push("success", { title, ...opts }),
  error: (title: string, opts: Omit<ToastInput, "title"> = {}) => useToasts.getState().push("error", { title, ...opts }),
  info: (title: string, opts: Omit<ToastInput, "title"> = {}) => useToasts.getState().push("info", { title, ...opts }),
  dismiss: (id: number) => useToasts.getState().dismiss(id),
};
