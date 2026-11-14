export interface Session {
  id: string;
  title: string;
  model_preference: string | null;
  message_count: number;
  total_tokens: number;
  total_cost_usd: number;
  created_at: string;
  updated_at: string;
}

export type RunMode = "auto" | "research" | "browse" | "quick";
export type RunStatus = "running" | "completed" | "failed" | "cancelled" | "blocked";
export type StepStatus = "pending" | "running" | "done" | "failed";

/** Saved messages, from GET /sessions/{id}/messages */
export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  model_used: string | null;
  latency_ms: number;
  created_at: string;
  metadata: {
    run_id: string;
    status: RunStatus;
    mode: RunMode;
    activity: AgentEvent[];
    last_frame: BrowserFrameData | null;
    tool_calls: number;
    browser_actions: number;
  } | null;
}

export interface LLMModel {
  id: string;
  display_name: string;
  provider: string;
  context_window: number;
  supports_tools: boolean;
  supports_vision: boolean;
  input_cost_per_1m: number;
  output_cost_per_1m: number;
}

// ---- Stream events (backend: app/chat/service.py) ----

export interface BrowserFrameData {
  call_id: string | null;
  url: string;
  title: string;
  mime: string;
  data: string;
  width: number;
  height: number;
  ts: number;
}

export interface BrowserActionData {
  call_id: string | null;
  action: string;
  target: string | null;
  value: string | null;
  url: string;
  title: string;
  ok: boolean;
  error: string | null;
  ts: number;
}

export type AgentEvent =
  | { event: "run_started"; data: { run_id: string; session_id: string; user_message_id: string; title: string | null } }
  | { event: "node"; data: { node: string; status: "started" | "completed" | "failed"; duration_ms?: number } }
  | { event: "plan"; data: { steps: { index: number; title: string; status: StepStatus }[] } }
  | { event: "plan_step"; data: { index: number; status: StepStatus } }
  | { event: "tool_start"; data: { call_id: string; tool: string; node: string; args: string } }
  | { event: "tool_end"; data: { call_id: string; tool: string; ok: boolean; duration_ms: number; result: string } }
  | { event: "browser_session"; data: { status: "open" | "closed"; provider?: string; live_url?: string | null } }
  | { event: "browser_action"; data: BrowserActionData }
  | { event: "browser_frame"; data: BrowserFrameData }
  | { event: "notice"; data: { message: string } }
  | { event: "content"; data: { content: string } }
  | { event: "blocked"; data: { reason: string | null } }
  | { event: "error"; data: { message: string } }
  | {
      event: "done";
      data: { message_id: string; status: RunStatus; latency_ms: number; model: string; tool_calls: number; browser_actions: number };
    };

// ---- View model ----

export interface ToolCall {
  id: string;
  tool: string;
  node: string;
  args: string;
  status: "running" | "ok" | "error";
  durationMs?: number;
  result?: string;
  actions: BrowserActionData[];
}

export interface PlanStep {
  index: number;
  title: string;
  status: StepStatus;
}

export interface Frame {
  callId: string | null;
  url: string;
  title: string;
  src: string;
  ts: number;
}

export type TimelineItem =
  | { kind: "tool"; id: string }
  | { kind: "phase"; id: string; node: string; status: "started" | "completed" | "failed"; durationMs?: number }
  | { kind: "notice"; id: string; message: string };

export interface Run {
  id: string;
  status: RunStatus;
  mode: RunMode;
  startedAt: number;
  endedAt?: number;
  activeNode: string | null;
  route: string | null;
  plan: PlanStep[];
  tools: Record<string, ToolCall>;
  timeline: TimelineItem[];
  frames: Frame[];
  browserOpen: boolean;
  answer: string | null;
  error: string | null;
  blockedReason: string | null;
  model: string | null;
  latencyMs: number | null;
}

export interface Turn {
  key: string;
  prompt: string;
  mode: RunMode;
  run: Run;
}
