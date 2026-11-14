"use client";

import { Moon, Sun } from "lucide-react";
import { setTheme, useTheme } from "@/lib/theme";

/** Light/dark slider: the thumb slides between a sun and a moon. */
export default function ThemeToggle({ className = "" }: { className?: string }) {
  const theme = useTheme();
  const dark = theme === "dark";

  return (
    <button
      type="button"
      role="switch"
      aria-checked={dark}
      aria-label="Dark mode"
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(dark ? "light" : "dark")}
      className={`relative inline-flex h-7 w-[52px] shrink-0 items-center rounded-full border border-line bg-surface-2 transition-colors hover:border-line-strong ${className}`}
    >
      <Sun className="absolute left-[7px] size-3.5 text-fg-3" aria-hidden="true" />
      <Moon className="absolute right-[7px] size-3.5 text-fg-3" aria-hidden="true" />
      <span
        aria-hidden="true"
        className={`absolute left-[3px] flex size-[22px] items-center justify-center rounded-full bg-canvas shadow-[0_1px_3px_rgb(0_0_0/0.18)] transition-transform duration-200 [transition-timing-function:var(--ease-out)] ${
          dark ? "translate-x-6" : "translate-x-0"
        } ${theme === null ? "opacity-0" : ""}`}
      >
        {dark ? <Moon className="size-3 text-fg" /> : <Sun className="size-3 text-fg" />}
      </span>
    </button>
  );
}
