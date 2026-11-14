import type { AgentEvent, Frame, Run, RunMode, StoredMessage, Turn } from "./types";

const MAX_FRAMES = 40;

export function newRun(mode: RunMode): Run {
  return {
    id: "",
    status: "running",
    mode,
    startedAt: Date.now(),
    activeNode: null,
    route: null,
    plan: [],
    tools: {},
    timeline: [],
    frames: [],
    browserOpen: false,
    answer: null,
    error: null,
    blockedReason: null,
    model: null,
    latencyMs: null,
  };
}

const VISIBLE_PHASES = new Set(["planner", "synthesizer", "direct_answer"]);

/** Pure reducer: apply one stream event to a run. */
export function applyEvent(run: Run, ev: AgentEvent): Run {
  switch (ev.event) {
    case "run_started":
      return { ...run, id: ev.data.run_id };

    case "node": {
      const { node, status, duration_ms } = ev.data;
      const next: Run = { ...run, activeNode: status === "started" ? node : run.activeNode === node ? null : run.activeNode };
      if (node !== "router" && status === "started" && !run.route) next.route = node;
      if (VISIBLE_PHASES.has(node)) {
        const id = `phase-${node}-${status === "started" ? run.timeline.length : ""}`;
        if (status === "started") {
          next.timeline = [...run.timeline, { kind: "phase", id, node, status }];
        } else {
          let idx = -1;
          for (let i = run.timeline.length - 1; i >= 0; i--) {
            const t = run.timeline[i];
            if (t.kind === "phase" && t.node === node && t.status === "started") { idx = i; break; }
          }
          if (idx >= 0) {
            next.timeline = run.timeline.map((t, i) => (i === idx ? { ...t, status, durationMs: duration_ms } as typeof t : t));
          }
        }
      }
      return next;
    }

    case "plan":
      return { ...run, plan: ev.data.steps.map((s) => ({ ...s })) };

    case "plan_step":
      return { ...run, plan: run.plan.map((s) => (s.index === ev.data.index ? { ...s, status: ev.data.status } : s)) };

    case "tool_start": {
      const d = ev.data;
      return {
        ...run,
        tools: { ...run.tools, [d.call_id]: { id: d.call_id, tool: d.tool, node: d.node, args: d.args, status: "running", actions: [] } },
        timeline: [...run.timeline, { kind: "tool", id: d.call_id }],
      };
    }

    case "tool_end": {
      const d = ev.data;
      const prev = run.tools[d.call_id];
      if (!prev) return run;
      return {
        ...run,
        tools: { ...run.tools, [d.call_id]: { ...prev, status: d.ok ? "ok" : "error", durationMs: d.duration_ms, result: d.result } },
      };
    }

    case "browser_session":
      return { ...run, browserOpen: ev.data.status === "open" };

    case "browser_action": {
      const d = ev.data;
      const tool = d.call_id ? run.tools[d.call_id] : undefined;
      if (!tool) return run;
      return { ...run, tools: { ...run.tools, [tool.id]: { ...tool, actions: [...tool.actions, d] } } };
    }

    case "browser_frame": {
      const d = ev.data;
      const frame: Frame = { callId: d.call_id, url: d.url, title: d.title, src: `data:${d.mime};base64,${d.data}`, ts: d.ts };
      return { ...run, frames: [...run.frames, frame].slice(-MAX_FRAMES) };
    }

    case "notice":
      return { ...run, timeline: [...run.timeline, { kind: "notice", id: `notice-${run.timeline.length}`, message: ev.data.message }] };

    case "content":
      return { ...run, answer: ev.data.content };

    case "blocked":
      return { ...run, blockedReason: ev.data.reason ?? "This request was blocked by the safety filter." };

    case "error":
      return { ...run, error: ev.data.message };

    case "done":
      return {
        ...run,
        status: ev.data.status,
        endedAt: Date.now(),
        activeNode: null,
        browserOpen: false,
        model: ev.data.model,
        latencyMs: ev.data.latency_ms,
        plan: run.plan.map((s) => (s.status === "running" ? { ...s, status: ev.data.status === "completed" ? "done" : "failed" } : s)),
        tools: Object.fromEntries(
          Object.entries(run.tools).map(([k, t]) => [k, t.status === "running" ? { ...t, status: "error" as const } : t]),
        ),
      };
  }
}

/** A run whose stream ended without a `done` event (network drop, user stop). */
export function interruptRun(run: Run, status: "cancelled" | "failed", message?: string): Run {
  if (run.status !== "running") return run;
  return {
    ...run,
    status,
    endedAt: Date.now(),
    activeNode: null,
    browserOpen: false,
    error: status === "failed" ? message ?? "Connection lost before the agent finished." : run.error,
    plan: run.plan.map((s) => (s.status === "running" ? { ...s, status: "failed" } : s)),
    tools: Object.fromEntries(Object.entries(run.tools).map(([k, t]) => [k, t.status === "running" ? { ...t, status: "error" as const } : t])),
  };
}

/** Rebuild turns from saved history: user message followed by its assistant run. */
export function turnsFromHistory(messages: StoredMessage[]): Turn[] {
  const turns: Turn[] = [];
  let pending: StoredMessage | null = null;
  for (const m of messages) {
    if (m.role === "user") {
      if (pending) turns.push(orphanTurn(pending));
      pending = m;
      continue;
    }
    const meta = m.metadata;
    let run = newRun(meta?.mode ?? "auto");
    for (const ev of meta?.activity ?? []) run = applyEvent(run, ev);
    if (meta?.last_frame) run = applyEvent(run, { event: "browser_frame", data: meta.last_frame });
    const status = meta?.status ?? "completed";
    run = {
      ...applyEvent(run, {
        event: "done",
        data: {
          message_id: m.id, status, latency_ms: m.latency_ms, model: m.model_used ?? "",
          tool_calls: meta?.tool_calls ?? 0, browser_actions: meta?.browser_actions ?? 0,
        },
      }),
      id: meta?.run_id ?? m.id,
      startedAt: new Date(m.created_at).getTime() - m.latency_ms,
      endedAt: new Date(m.created_at).getTime(),
    };
    if (status === "completed") run.answer = m.content;
    else if (status === "blocked") run.blockedReason = m.content;
    else if (status === "failed") run.error = m.content;
    else run.answer = null;
    turns.push({ key: m.id, prompt: pending?.content ?? "", mode: run.mode, run });
    pending = null;
  }
  if (pending) turns.push(orphanTurn(pending));
  return turns;
}

function orphanTurn(user: StoredMessage): Turn {
  const run = { ...newRun("auto"), status: "failed" as const, error: "No response was recorded for this message.", endedAt: Date.now() };
  return { key: user.id, prompt: user.content, mode: "auto", run };
}

export function runSummary(run: Run): string {
  const tools = Object.values(run.tools);
  const actions = tools.reduce((n, t) => n + t.actions.length, 0);
  const parts: string[] = [];
  if (run.plan.length) parts.push(`${run.plan.length} step${run.plan.length === 1 ? "" : "s"}`);
  if (actions) parts.push(`${actions} browser action${actions === 1 ? "" : "s"}`);
  else if (tools.length) parts.push(`${tools.length} tool call${tools.length === 1 ? "" : "s"}`);
  return parts.join(" · ");
}

export function formatDuration(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}

export function hostOf(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
}
