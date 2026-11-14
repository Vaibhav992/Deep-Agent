"use client";

import { useEffect, useRef, useState } from "react";
import { EASE_IN_OUT, EASE_OUT, FULL_MOTION, REDUCED_MOTION, gsap, useGSAP } from "@/lib/gsap";
import {
  AlertTriangle, ArrowLeft, Brain, Check, ChevronDown, Circle, Database, FileText, Globe, Hourglass,
  Link2, ListTree, Loader2, MousePointerClick, MoveVertical, PenLine, Search, Keyboard, X, Monitor,
} from "lucide-react";
import { formatDuration, hostOf, runSummary } from "@/lib/run";
import type { BrowserActionData, Run, ToolCall } from "@/lib/types";
import { StatusDot } from "./ui";

const RUNNING_LABEL: Record<string, string> = {
  router: "Thinking",
  planner: "Planning",
  researcher: "Researching",
  browser_agent: "Browsing",
  synthesizer: "Writing the answer",
  direct_answer: "Answering",
};

const DONE_LABEL: Record<Exclude<Run["status"], "running">, string> = {
  completed: "Done",
  failed: "Failed",
  cancelled: "Stopped",
  blocked: "Blocked",
};

function statusLabel(run: Run): string {
  if (run.status !== "running") return DONE_LABEL[run.status];
  const node = run.activeNode ?? "router";
  if (node === "researcher") {
    const i = run.plan.findIndex((s) => s.status === "running");
    if (i >= 0) return `Researching · step ${i + 1} of ${run.plan.length}`;
  }
  return RUNNING_LABEL[node] ?? "Working";
}

function useElapsed(run: Run): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (run.status !== "running") return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [run.status]);
  return (run.endedAt ?? now) - run.startedAt;
}

function parseArgs(args: string): Record<string, unknown> {
  try {
    return JSON.parse(args);
  } catch {
    return {};
  }
}

const ACTION_ICON: Record<string, typeof Globe> = {
  navigate: Globe, click: MousePointerClick, type: Keyboard, scroll: MoveVertical,
  extract: FileText, inspect: ListTree, wait: Hourglass, back: ArrowLeft,
};

function describeAction(a: BrowserActionData): string {
  switch (a.action) {
    case "navigate": return a.ok ? `Opened ${hostOf(a.url || a.target || "")}` : `Couldn't open ${a.target ?? "the page"}`;
    case "click": return `Clicked ${a.target ?? "an element"}`;
    case "type": return `Typed “${a.value ?? ""}” into ${a.target ?? "a field"}`;
    case "scroll": return `Scrolled ${a.target ?? "down"}`;
    case "extract": return a.target === "links" ? "Collected the page's links" : "Read the page text";
    case "inspect": return "Inspected the page structure";
    case "wait": return `Waited ${a.target ?? ""} for the page`;
    case "back": return "Went back";
    default: return a.action;
  }
}

function describeTool(t: ToolCall): { icon: typeof Globe; text: string; detail?: string } {
  const args = parseArgs(t.args);
  const action = t.actions[t.actions.length - 1];
  if (t.tool.startsWith("browser_")) {
    if (action) return { icon: ACTION_ICON[action.action] ?? Monitor, text: describeAction(action), detail: action.error ?? undefined };
    if (t.tool === "browser_navigate") return { icon: Globe, text: `Opening ${hostOf(String(args.url ?? ""))}` };
    return { icon: Monitor, text: t.tool.replace("browser_", "").replaceAll("_", " ") };
  }
  switch (t.tool) {
    case "web_search": return { icon: Search, text: `Searched the web`, detail: String(args.query ?? "") };
    case "read_url": return { icon: Link2, text: `Read ${hostOf(String(args.url ?? ""))}` };
    case "think": return { icon: Brain, text: "Reasoned through the problem" };
    case "search_memory": return { icon: Database, text: "Searched memory", detail: String(args.query ?? "") };
    case "write_memory": return { icon: PenLine, text: "Saved to memory" };
    default: return { icon: Circle, text: t.tool };
  }
}

function RowStatus({ status }: { status: ToolCall["status"] }) {
  if (status === "running") return <Loader2 className="size-3.5 animate-spin text-signal" aria-label="Running" />;
  if (status === "error") return <X className="size-3.5 text-danger" aria-label="Failed" />;
  return <Check className="size-3.5 text-fg-3" aria-label="Done" />;
}

function ToolRow({ tool }: { tool: ToolCall }) {
  const [open, setOpen] = useState(false);
  const { icon: Icon, text, detail } = describeTool(tool);
  return (
    <li className="enter">
      <button
        onClick={() => setOpen((o) => !o)}
        className="group flex w-full items-center gap-2.5 rounded-md py-1.5 pl-1 pr-2 text-left transition-colors hover:bg-surface-2"
        aria-expanded={open}
      >
        <Icon className={`size-3.5 shrink-0 ${tool.status === "running" ? "text-signal" : "text-fg-3"}`} />
        <span className={`min-w-0 flex-1 truncate text-[13px] ${tool.status === "error" ? "text-danger" : tool.status === "running" ? "text-fg" : "text-fg-2"}`}>
          {text}
          {detail && <span className="ml-1.5 font-mono text-[12px] text-fg-3">{detail}</span>}
        </span>
        {tool.durationMs !== undefined && (
          <span className="tabular font-mono text-[11px] text-fg-3">{(tool.durationMs / 1000).toFixed(1)}s</span>
        )}
        <RowStatus status={tool.status} />
      </button>
      {open && (
        <div className="mb-1 ml-7 mr-2 space-y-1.5 rounded-[10px] bg-surface-2 p-2.5 font-mono text-[11.5px] leading-[18px] text-fg-2">
          <div><span className="text-fg-3">tool </span>{tool.tool}</div>
          {tool.args !== "{}" && <div className="break-all"><span className="text-fg-3">args </span>{tool.args}</div>}
          {tool.result && <div className="break-words"><span className="text-fg-3">result </span>{tool.result}</div>}
          {tool.status === "running" && <div className="text-fg-3">waiting for result…</div>}
        </div>
      )}
    </li>
  );
}

function PlanList({ run }: { run: Run }) {
  return (
    <ol className="mb-2 space-y-1" aria-label="Plan">
      {run.plan.map((s) => (
        <li key={s.index} className="flex items-start gap-2.5 py-0.5 pl-1">
          <span
            className={`mt-[3px] flex size-4 shrink-0 items-center justify-center rounded-full border font-mono text-[10px] ${
              s.status === "running" ? "border-signal text-signal"
                : s.status === "done" ? "border-line-strong bg-surface-3 text-fg-2"
                : s.status === "failed" ? "border-danger text-danger" : "border-line text-fg-3"
            }`}
          >
            {s.status === "done" ? <Check className="size-2.5" /> : s.index + 1}
          </span>
          <span className={`text-[13px] leading-[22px] ${s.status === "running" ? "text-fg" : s.status === "pending" ? "text-fg-3" : "text-fg-2"}`}>
            {s.title}
          </span>
        </li>
      ))}
    </ol>
  );
}

export default function RunCard({
  run,
  onShowBrowser,
  browserFocused,
}: {
  run: Run;
  onShowBrowser: () => void;
  browserFocused: boolean;
}) {
  const running = run.status === "running";
  // Open while the agent works, collapsed to a summary afterwards, unless the user chose otherwise.
  const [userExpanded, setUserExpanded] = useState<boolean | null>(null);
  const expanded = userExpanded ?? running;
  const setExpanded = (fn: (e: boolean) => boolean) => setUserExpanded(fn(expanded));
  const elapsed = useElapsed(run);

  const tools = run.timeline.filter((t) => t.kind !== "phase");
  const hasActivity = run.plan.length > 0 || tools.length > 0;
  const summary = runSummary(run);
  const latestFrame = run.frames[run.frames.length - 1];

  // When a live run finishes, keep the timeline mounted while it folds away (see useGSAP below).
  const [prevRunning, setPrevRunning] = useState(running);
  const [folding, setFolding] = useState(false);
  if (prevRunning !== running) {
    setPrevRunning(running);
    if (!running && userExpanded === null && hasActivity) setFolding(true);
  }
  const showBody = hasActivity && (expanded || folding);

  const cardRef = useRef<HTMLElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const body = bodyRef.current;
      if (!folding || !body) return;
      const mm = gsap.matchMedia();
      mm.add({ reduce: REDUCED_MOTION, full: FULL_MOTION }, (ctx) => {
        const tl = gsap.timeline({ onComplete: () => setFolding(false) });
        if (ctx.conditions?.reduce) {
          tl.to(body, { opacity: 0, duration: 0.2 });
          return;
        }
        // Rows leave bottom-up, then the panel folds: a single, deliberate "this run is done" beat.
        tl.to(body.querySelectorAll("li"), {
          opacity: 0, y: -4, duration: 0.16, ease: EASE_OUT, stagger: { each: 0.018, from: "end" },
        }).to(body, { height: 0, paddingTop: 0, paddingBottom: 0, opacity: 0, duration: 0.38, ease: EASE_IN_OUT }, "-=0.06");
      });
      return () => mm.revert();
    },
    { dependencies: [folding], scope: cardRef },
  );

  return (
    <section
      ref={cardRef}
      className={`overflow-hidden rounded-[14px] border bg-canvas transition-colors duration-300 ${running ? "border-line-strong" : "border-line"}`}
      aria-label="Agent activity"
    >
      <header className="flex items-center gap-2.5 px-3.5 py-2.5">
        <StatusDot status={run.status} />
        <span
          key={running ? "running" : run.status}
          className={`text-[13px] ${running ? "text-fg" : `swap-in ${run.status === "failed" ? "text-danger" : "text-fg-2"}`}`}
          aria-live="polite"
        >
          {statusLabel(run)}
        </span>
        <span className="tabular font-mono text-[12px] text-fg-3">{formatDuration(elapsed)}</span>
        {!running && summary && <span className="swap-in hidden truncate text-[12px] text-fg-3 sm:inline">· {summary}</span>}
        <div className="ml-auto flex items-center gap-1">
          {latestFrame && (
            <button
              onClick={onShowBrowser}
              className={`press flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] transition-colors ${
                browserFocused ? "bg-ink text-on-ink" : "text-fg-2 hover:bg-surface-2 hover:text-fg"
              }`}
            >
              <Monitor className="size-3.5" />
              Browser
            </button>
          )}
          {hasActivity && (
            <button
              onClick={() => setExpanded((e) => !e)}
              className="rounded-md p-1 text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg"
              aria-label={expanded ? "Hide activity" : "Show activity"}
              aria-expanded={expanded}
            >
              <ChevronDown className={`size-4 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`} />
            </button>
          )}
        </div>
      </header>

      {showBody && (
        <div ref={bodyRef} className="overflow-hidden border-t border-line px-2.5 py-2">
          {run.plan.length > 0 && <PlanList run={run} />}
          <ul className="space-y-0.5">
            {tools.map((item) =>
              item.kind === "tool" ? (
                run.tools[item.id] && <ToolRow key={item.id} tool={run.tools[item.id]} />
              ) : item.kind === "notice" ? (
                <li key={item.id} className="flex items-center gap-2.5 py-1.5 pl-1 text-[13px] text-warn">
                  <AlertTriangle className="size-3.5" />
                  {item.message}
                </li>
              ) : null,
            )}
          </ul>
        </div>
      )}

      {running && !hasActivity && (
        <div className="space-y-2 border-t border-line px-3.5 py-3">
          <div className="skeleton h-3 w-2/3 rounded" />
          <div className="skeleton h-3 w-1/2 rounded" />
        </div>
      )}
    </section>
  );
}
