"use client";

import { useSyncExternalStore } from "react";
import type { RunStatus } from "@/lib/types";

const noopSubscribe = () => () => {};

/** Current time on the client; null during prerender so render output never bakes in a build-time clock. */
export function useClientNow(): Date | null {
  return useSyncExternalStore(noopSubscribe, getNowMinute, () => null);
}

let cachedNow: Date | null = null;
function getNowMinute(): Date {
  // useSyncExternalStore needs a stable snapshot: reuse the same Date within a minute.
  const now = Date.now();
  if (!cachedNow || now - cachedNow.getTime() > 60_000) cachedNow = new Date(now);
  return cachedNow;
}

export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="1.5" y="1.5" width="21" height="21" rx="5" stroke="var(--signal)" strokeWidth="2" />
      <path d="M7 7.5h10L9.5 17.5" stroke="var(--signal)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="flex items-center gap-2.5">
      <Logo />
      <span className="text-[15px] font-medium tracking-[-0.01em]">Deep Agent</span>
    </span>
  );
}

const DOT: Record<RunStatus, string> = {
  running: "bg-signal live-dot",
  completed: "bg-fg-3",
  cancelled: "bg-fg-3",
  failed: "bg-danger",
  blocked: "bg-warn",
};

export function StatusDot({ status, className = "" }: { status: RunStatus; className?: string }) {
  return <span className={`inline-block size-1.5 shrink-0 rounded-full ${DOT[status]} ${className}`} aria-hidden="true" />;
}

export function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="rounded border border-line bg-surface-2 px-1 font-mono text-[11px] leading-4 text-fg-3">{children}</kbd>
  );
}
