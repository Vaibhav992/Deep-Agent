"use client";

import { useSyncExternalStore } from "react";
import { THEME_STORAGE_KEY as KEY } from "./theme-script";

export type Theme = "light" | "dark";

const listeners = new Set<() => void>();

function resolved(): Theme {
  const explicit = document.documentElement.dataset.theme;
  if (explicit === "light" || explicit === "dark") return explicit;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  mq.addEventListener("change", cb);
  return () => {
    listeners.delete(cb);
    mq.removeEventListener("change", cb);
  };
}

export function setTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // Storage unavailable: the choice lasts for this page only.
  }
  listeners.forEach((l) => l());
}

/** The theme currently shown; null during prerender (the server can't know it). */
export function useTheme(): Theme | null {
  return useSyncExternalStore(subscribe, resolved, () => null);
}
