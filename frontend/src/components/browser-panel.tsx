"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Lock, Monitor, X } from "lucide-react";
import { hostOf } from "@/lib/run";
import { useChatStore } from "@/store/chat-store";
import type { BrowserActionData } from "@/lib/types";

function actionLine(a: BrowserActionData): string {
  switch (a.action) {
    case "navigate": return `open ${a.target ?? a.url}`;
    case "click": return `click ${a.target ?? ""}`;
    case "type": return `type "${a.value ?? ""}" → ${a.target ?? ""}`;
    case "scroll": return `scroll ${a.target ?? ""}`;
    case "extract": return `read ${a.target ?? "page"}`;
    case "inspect": return "inspect page";
    case "wait": return `wait ${a.target ?? ""}`;
    case "back": return "back";
    default: return a.action;
  }
}

export default function BrowserPanel({ onClose }: { onClose: () => void }) {
  const turn = useChatStore((s) => s.turns.find((t) => t.key === s.focusedTurnKey) ?? null);
  const run = turn?.run;
  const frames = useMemo(() => run?.frames ?? [], [run?.frames]);
  const live = run?.status === "running" && run.browserOpen;
  // Follow the newest frame unless the user has scrubbed back in this turn.
  const [pick, setPick] = useState<{ turn: string; index: number } | null>(null);
  const selected = pick && pick.turn === turn?.key ? pick.index : null;
  const setSelected = (i: number | null) => setPick(i === null || !turn ? null : { turn: turn.key, index: i });
  const index = selected ?? frames.length - 1;
  const frame = frames[index];
  const prevFrame = index > 0 ? frames[index - 1] : null;
  // A browser action is in flight: show the loading sweep over the live view.
  const loading =
    live && selected === null && Object.values(run?.tools ?? {}).some((t) => t.status === "running" && t.tool.startsWith("browser_"));

  const actions = useMemo(
    () => (run ? run.timeline.flatMap((t) => (t.kind === "tool" && run.tools[t.id] ? run.tools[t.id].actions : [])) : []),
    [run],
  );

  return (
    <aside className="flex h-full flex-col bg-surface-1" aria-label="Browser">
      <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line px-4">
        <Monitor className="size-4 text-fg-2" />
        <span className="text-[13px] font-medium">Browser</span>
        {live && (
          <span className="ml-1 eyebrow flex items-center gap-1.5 rounded-full bg-signal-wash px-2 py-0.5 text-signal">
            <span className="live-dot size-1.5 rounded-full bg-signal" />
            Live
          </span>
        )}
        <button onClick={onClose} className="ml-auto rounded-md p-1.5 text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg" aria-label="Close browser panel">
          <X className="size-4" />
        </button>
      </header>

      {!frame ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-8 text-center">
          <Monitor className="size-6 text-fg-3" />
          <p className="text-[13px] text-fg-2">{live ? "Opening the browser…" : "No browser activity in this task."}</p>
          <p className="text-[12px] text-fg-3">When the agent uses the browser, you&apos;ll see each page here as it works.</p>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="p-3">
            <div className="overflow-hidden rounded-[14px] border border-line bg-canvas shadow-[0_8px_24px_rgb(23_23_28/0.06)]">
              <div className="flex items-center gap-2 border-b border-line bg-surface-2 px-2.5 py-1.5">
                <div className="flex gap-1 text-fg-3" aria-hidden="true">
                  <ChevronLeft className="size-3.5" />
                  <ChevronRight className="size-3.5" />
                </div>
                <div className="flex min-w-0 flex-1 items-center gap-1.5 rounded-md bg-surface-1 px-2 py-1">
                  {frame.url.startsWith("https://") && <Lock className="size-3 shrink-0 text-fg-3" />}
                  <span className="truncate font-mono text-[11.5px] text-fg-2" title={frame.url}>{frame.url}</span>
                </div>
              </div>
              {/* Real screenshots from the agent's browser session: the new one settles over the previous */}
              <div className="relative aspect-[16/10] w-full overflow-hidden">
                {prevFrame && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={prevFrame.src} alt="" aria-hidden="true" className="absolute inset-0 size-full object-cover object-top" />
                )}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  key={frame.src.length + ":" + frame.ts}
                  src={frame.src}
                  alt={`Browser screenshot of ${frame.title || hostOf(frame.url)}`}
                  className="frame-in absolute inset-0 size-full object-cover object-top"
                />
                {loading && (
                  <div className="pointer-events-none absolute inset-0" aria-hidden="true">
                    <div className="scan-line h-full w-full bg-[linear-gradient(to_bottom,transparent_calc(100%-2px),var(--signal)_calc(100%-2px))] opacity-70" />
                  </div>
                )}
              </div>
            </div>
            <div className="mt-2 flex items-center gap-2 px-0.5">
              <span className="truncate text-[12px] text-fg-2">{frame.title || hostOf(frame.url)}</span>
              <span className="ml-auto shrink-0 font-mono text-[11px] text-fg-3 tabular">
                {index + 1}/{frames.length}
              </span>
            </div>
          </div>

          {frames.length > 1 && (
            <div className="flex gap-1.5 overflow-x-auto px-3 pb-3" role="listbox" aria-label="Screenshots">
              {frames.map((f, i) => (
                <button
                  key={`${f.ts}-${i}`}
                  role="option"
                  aria-selected={i === index}
                  onClick={() => setSelected(i === frames.length - 1 ? null : i)}
                  className={`press shrink-0 overflow-hidden rounded-md border transition-colors ${i === index ? "border-ink" : "border-line hover:border-line-strong"}`}
                  title={f.title || f.url}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={f.src} alt="" className="h-10 w-16 object-cover object-top" />
                </button>
              ))}
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto border-t border-line px-3 py-2">
            <h3 className="eyebrow px-1 pb-1.5 text-fg-3">Actions</h3>
            <ol className="space-y-0.5">
              {actions.map((a, i) => (
                <li key={`${a.ts}-${i}`} className="flex items-baseline gap-2 rounded px-1 py-0.5 font-mono text-[11.5px] leading-[18px]">
                  <span className="w-5 shrink-0 text-right text-fg-3 tabular">{i + 1}</span>
                  <span className={`min-w-0 flex-1 break-words ${a.ok ? "text-fg-2" : "text-danger"}`}>
                    {actionLine(a)}
                    {a.error && <span className="block text-danger/80">{a.error}</span>}
                  </span>
                  <span className="shrink-0 text-fg-3">{hostOf(a.url)}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </aside>
  );
}
