"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Square } from "lucide-react";
import type { RunMode } from "@/lib/types";

const MODES: { value: RunMode; label: string; hint: string }[] = [
  { value: "auto", label: "Auto", hint: "The agent decides how to handle the task" },
  { value: "research", label: "Research", hint: "Plan, search the web, then write a cited answer" },
  { value: "browse", label: "Browse", hint: "Work in a real browser" },
  { value: "quick", label: "Quick", hint: "Answer directly, no tools" },
];

export default function Composer({
  onSubmit,
  onStop,
  running,
  disabled = false,
  autoFocus = false,
  initialValue = "",
  placeholder = "Describe a task…",
  large = false,
}: {
  onSubmit: (prompt: string, mode: RunMode) => void;
  onStop: () => void;
  running: boolean;
  disabled?: boolean;
  autoFocus?: boolean;
  initialValue?: string;
  placeholder?: string;
  large?: boolean;
}) {
  // Parent remounts the composer (via `key`) to load a new draft such as a starter task.
  const [value, setValue] = useState(initialValue);
  const [mode, setMode] = useState<RunMode>("auto");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, window.innerHeight * 0.4)}px`;
  }, [value]);

  const canSend = value.trim().length > 0 && !running && !disabled;

  function submit() {
    if (!canSend) return;
    onSubmit(value.trim(), mode);
    setValue("");
  }

  return (
    <div className="rounded-[14px] border border-line bg-surface-2 transition-colors focus-within:border-line-strong">
      <textarea
        ref={ref}
        value={value}
        autoFocus={autoFocus}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
        rows={large ? 3 : 1}
        maxLength={8000}
        placeholder={placeholder}
        aria-label="Task for the agent"
        className={`block w-full resize-none bg-transparent px-4 pt-3.5 text-fg placeholder:text-fg-3 focus:outline-none ${
          large ? "min-h-[84px] text-[15px] leading-6" : "min-h-[24px] text-[14px] leading-6"
        }`}
      />
      <div className="flex items-center gap-2 px-2.5 pb-2.5 pt-2">
        <div className="flex rounded-lg border border-line bg-surface-1 p-0.5" role="radiogroup" aria-label="Mode">
          {MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              role="radio"
              aria-checked={mode === m.value}
              title={m.hint}
              onClick={() => setMode(m.value)}
              className={`rounded-md px-2.5 py-1 text-[12px] leading-4 transition-colors ${
                mode === m.value ? "bg-surface-3 text-fg" : "text-fg-3 hover:text-fg-2"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <span className="ml-auto hidden truncate text-[12px] text-fg-3 sm:inline">
          {running ? "Agent is working" : "Enter to send"}
        </span>
        {running ? (
          <button
            type="button"
            onClick={onStop}
            className="flex h-8 items-center gap-1.5 rounded-lg border border-line-strong bg-surface-3 px-3 text-[13px] text-fg transition-colors hover:border-danger hover:text-danger"
            aria-label="Stop the agent"
          >
            <Square className="size-3 fill-current" />
            Stop
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!canSend}
            className="flex size-8 items-center justify-center rounded-lg bg-signal text-signal-ink transition-opacity disabled:opacity-30"
            aria-label="Send"
          >
            <ArrowUp className="size-4" strokeWidth={2.5} />
          </button>
        )}
      </div>
    </div>
  );
}
