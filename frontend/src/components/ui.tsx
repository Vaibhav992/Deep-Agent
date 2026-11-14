"use client";

import { useSyncExternalStore } from "react";
import type { RunStatus } from "@/lib/types";
import { WORDMARK } from "@/lib/brand";

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

/**
 * The Dhyanik mark: an open ensō (the uncluttered, awakened mind) with a bindu, a single point of
 * focus, resting in its opening. Read together it is also a seated figure in meditation.
 * `tone="auto"` follows the theme; `tone="onDark"` is for surfaces that are dark in both themes.
 */
export function Logo({ size = 24, tone = "auto" }: { size?: number; tone?: "auto" | "onDark" }) {
  const arc = tone === "onDark" ? "#e5f4ef" : "var(--logo-arc)";
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path d={ENSO_PATH} stroke={arc} strokeWidth="3.2" strokeLinecap="round" />
      <circle cx="16" cy="8.2" r="2.7" fill="var(--saffron)" />
    </svg>
  );
}

// Circle centred at (16,18), r 10.5, open across the top (from 300° round to 240°).
export const ENSO_PATH = "M21.25 8.907A10.5 10.5 0 1 1 10.75 8.907";

export function Wordmark({ tone = "auto" }: { tone?: "auto" | "onDark" }) {
  return (
    <span className="flex items-center gap-2">
      <Logo tone={tone} />
      <span className="font-display text-[19px] leading-none tracking-[-0.045em]">{WORDMARK}</span>
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
