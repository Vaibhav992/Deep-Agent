import { create } from "zustand";
import { applyEvent, interruptRun, newRun } from "@/lib/run";
import type { AgentEvent, RunMode, Session, Turn } from "@/lib/types";

interface ChatState {
  sessions: Session[];
  sessionsLoaded: boolean;
  turns: Turn[];
  turnsSessionId: string | null;
  /** Turn whose browser activity is shown in the browser panel. */
  focusedTurnKey: string | null;
  browserPanelOpen: boolean;

  setSessions: (sessions: Session[]) => void;
  upsertSession: (session: Session) => void;
  patchSession: (id: string, data: Partial<Session>) => void;
  removeSession: (id: string) => void;

  setTurns: (sessionId: string | null, turns: Turn[]) => void;
  startTurn: (key: string, prompt: string, mode: RunMode) => void;
  applyToTurn: (key: string, ev: AgentEvent) => void;
  interruptTurn: (key: string, status: "cancelled" | "failed", message?: string) => void;

  focusBrowser: (key: string | null) => void;
  setBrowserPanelOpen: (open: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  sessions: [],
  sessionsLoaded: false,
  turns: [],
  turnsSessionId: null,
  focusedTurnKey: null,
  browserPanelOpen: false,

  setSessions: (sessions) => set({ sessions, sessionsLoaded: true }),
  upsertSession: (session) =>
    set((s) => ({ sessions: [session, ...s.sessions.filter((x) => x.id !== session.id)] })),
  patchSession: (id, data) =>
    set((s) => ({ sessions: s.sessions.map((x) => (x.id === id ? { ...x, ...data } : x)) })),
  removeSession: (id) => set((s) => ({ sessions: s.sessions.filter((x) => x.id !== id) })),

  setTurns: (sessionId, turns) => {
    const withBrowser = [...turns].reverse().find((t) => t.run.frames.length > 0);
    set({ turns, turnsSessionId: sessionId, focusedTurnKey: withBrowser?.key ?? null, browserPanelOpen: false });
  },
  startTurn: (key, prompt, mode) =>
    set((s) => ({ turns: [...s.turns, { key, prompt, mode, run: newRun(mode) }] })),
  applyToTurn: (key, ev) =>
    set((s) => {
      const turns = s.turns.map((t) => (t.key === key ? { ...t, run: applyEvent(t.run, ev) } : t));
      // The first browser activity of a run brings the browser panel into view.
      const opensBrowser = (ev.event === "browser_session" && ev.data.status === "open") || ev.event === "browser_frame";
      return opensBrowser && s.focusedTurnKey !== key
        ? { turns, focusedTurnKey: key, browserPanelOpen: true }
        : { turns };
    }),
  interruptTurn: (key, status, message) =>
    set((s) => ({ turns: s.turns.map((t) => (t.key === key ? { ...t, run: interruptRun(t.run, status, message) } : t)) })),

  focusBrowser: (key) => set({ focusedTurnKey: key, browserPanelOpen: key !== null }),
  setBrowserPanelOpen: (open) => set({ browserPanelOpen: open }),
}));
