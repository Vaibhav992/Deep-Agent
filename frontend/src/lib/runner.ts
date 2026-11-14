import { ApiError, streamRun } from "./api";
import { useChatStore } from "@/store/chat-store";
import type { RunMode } from "./types";
import { create } from "zustand";

type TokenGetter = () => Promise<string | null>;

interface ActiveRun {
  sessionId: string;
  turnKey: string;
}

/** The single in-flight run (one at a time per tab). Kept outside components so it survives navigation. */
export const useActiveRun = create<{ active: ActiveRun | null }>(() => ({ active: null }));

let controller: AbortController | null = null;

export async function startRun(
  getToken: TokenGetter,
  opts: { sessionId: string; prompt: string; mode: RunMode; model?: string | null },
): Promise<void> {
  if (controller) return;
  const store = useChatStore.getState();
  const turnKey = `turn-${Date.now()}`;
  store.startTurn(turnKey, opts.prompt, opts.mode);
  controller = new AbortController();
  useActiveRun.setState({ active: { sessionId: opts.sessionId, turnKey } });

  let sawDone = false;
  try {
    await streamRun(
      getToken,
      { sessionId: opts.sessionId, message: opts.prompt, mode: opts.mode, model: opts.model },
      (ev) => {
        if (ev.event === "done") sawDone = true;
        if (ev.event === "run_started" && ev.data.title) {
          useChatStore.getState().patchSession(opts.sessionId, { title: ev.data.title, updated_at: new Date().toISOString() });
        }
        useChatStore.getState().applyToTurn(turnKey, ev);
      },
      controller.signal,
    );
    if (!sawDone) useChatStore.getState().interruptTurn(turnKey, "failed");
  } catch (err) {
    const aborted = controller?.signal.aborted;
    const message =
      err instanceof ApiError ? err.message : "Couldn't reach the agent server. Check your connection and try again.";
    useChatStore.getState().interruptTurn(turnKey, aborted ? "cancelled" : "failed", message);
  } finally {
    controller = null;
    useActiveRun.setState({ active: null });
  }
}

/** Stop the current run. Closing the stream cancels it on the server, which saves it as "cancelled". */
export function stopRun(): void {
  controller?.abort();
}
