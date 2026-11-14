"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth, useUser } from "@clerk/nextjs";
import { Globe, Search, Zap } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { turnsFromHistory } from "@/lib/run";
import { startRun, stopRun, useActiveRun } from "@/lib/runner";
import { useChatStore } from "@/store/chat-store";
import type { RunMode, Session, StoredMessage, Turn } from "@/lib/types";
import Composer from "./composer";
import TurnView from "./turn-view";
import { useClientNow } from "./ui";

const STARTERS: { icon: typeof Globe; label: string; prompt: string }[] = [
  { icon: Search, label: "Research", prompt: "Compare the latest pricing and context limits of the main frontier LLM APIs, with sources." },
  { icon: Globe, label: "Browse", prompt: "Open https://news.ycombinator.com and summarise the top 5 stories with their links." },
  { icon: Zap, label: "Quick", prompt: "Explain the difference between a process and a thread in two short paragraphs." },
];

const NO_TURNS: Turn[] = [];

function greeting(name: string | null | undefined, now: Date | null) {
  if (!now) return name ? `Hello, ${name}.` : "Hello.";
  const h = now.getHours();
  const part = h < 5 ? "Working late" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  return name ? `${part}, ${name}.` : `${part}.`;
}

export default function Workspace({ sessionId }: { sessionId: string | null }) {
  const { getToken } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const turns = useChatStore((s) => (s.turnsSessionId === sessionId ? s.turns : NO_TURNS));
  const turnsSessionId = useChatStore((s) => s.turnsSessionId);
  const { setTurns, upsertSession } = useChatStore.getState();
  const active = useActiveRun((s) => s.active);
  const now = useClientNow();
  const running = active !== null;
  const [loadErrorFor, setLoadErrorFor] = useState<{ id: string; message: string } | null>(null);
  const loadError = loadErrorFor && loadErrorFor.id === sessionId ? loadErrorFor.message : null;
  const loading = sessionId !== null && turnsSessionId !== sessionId && !loadError;
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ key: 0, text: "" });
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  // Load the conversation unless it's already in memory (e.g. we just created it and a run is streaming).
  useEffect(() => {
    if (!sessionId) {
      if (!running) setTurns(null, []);
      return;
    }
    if (turnsSessionId === sessionId) return;
    let cancelled = false;
    api
      .get<StoredMessage[]>(getToken, `/sessions/${sessionId}/messages`)
      .then((messages) => !cancelled && setTurns(sessionId, turnsFromHistory(messages)))
      .catch((e) => {
        if (cancelled) return;
        setLoadErrorFor({
          id: sessionId,
          message: e instanceof ApiError && e.status === 404 ? "This task doesn't exist or was deleted." : "Couldn't load this task.",
        });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && stickToBottom.current) el.scrollTo({ top: el.scrollHeight });
  }, [turns]);

  const submit = useCallback(
    async (prompt: string, mode: RunMode) => {
      setSubmitError(null);
      let id = sessionId;
      if (!id) {
        try {
          const session = await api.post<Session>(getToken, "/sessions", { title: "New Chat" });
          upsertSession(session);
          setTurns(session.id, []);
          id = session.id;
          router.replace(`/chat/${session.id}`);
        } catch {
          setSubmitError("Couldn't start a new task. Check that the agent server is running.");
          setDraft({ key: Date.now(), text: prompt });
          return;
        }
      }
      stickToBottom.current = true;
      let model: string | null = null;
      try {
        model = window.localStorage.getItem("deep-agent:model");
      } catch {
        // Storage unavailable: use the server's automatic model choice.
      }
      void startRun(getToken, { sessionId: id, prompt, mode, model });
    },
    [sessionId, getToken, router, setTurns, upsertSession],
  );

  const busyElsewhere = running && active?.sessionId !== sessionId;
  const composer = (large: boolean) => (
    <>
      <Composer
        key={draft.key}
        onSubmit={submit}
        onStop={stopRun}
        running={running && !busyElsewhere}
        disabled={busyElsewhere}
        initialValue={draft.text}
        autoFocus
        large={large}
        placeholder={large ? "Give the agent a task: research a topic, or open a site and get something done…" : "Ask a follow-up or give a new task…"}
      />
      {busyElsewhere && <p className="mt-2 text-[12px] text-fg-3">Another task is still running. Stop it or wait for it to finish.</p>}
      {submitError && <p className="mt-2 text-[12px] text-danger" role="alert">{submitError}</p>}
    </>
  );

  if (loadError) {
    return (
      <div className="flex flex-1 items-center justify-center px-6">
        <div className="text-center">
          <p className="text-[14px] text-fg">{loadError}</p>
          <button onClick={() => router.push("/chat")} className="mt-3 text-[13px] text-fg-2 underline underline-offset-4 hover:text-fg">
            Start a new task
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="mx-auto w-full max-w-[760px] space-y-4 px-6 pt-16">
        <div className="skeleton ml-auto h-10 w-1/2 rounded-[10px]" />
        <div className="skeleton h-11 w-full rounded-[10px]" />
        <div className="skeleton h-4 w-5/6 rounded" />
        <div className="skeleton h-4 w-2/3 rounded" />
      </div>
    );
  }

  if (turns.length === 0) {
    return (
      <div className="relative flex flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-10 sm:px-6">
        <div
          className="pointer-events-none absolute left-1/2 top-[18%] h-[380px] w-[620px] -translate-x-1/2 rounded-full opacity-60 blur-[90px]"
          style={{ background: "radial-gradient(closest-side, #1e2a12, transparent)" }}
          aria-hidden="true"
        />
        <div className="relative w-full max-w-[680px]">
          <h1 className="text-[28px] font-semibold leading-[34px] tracking-[-0.02em]">{greeting(user?.firstName, now)}</h1>
          <p className="mt-1.5 text-[15px] text-fg-2">What should the agent work on?</p>
          <div className="mt-6">{composer(true)}</div>
          <div className="mt-5 grid gap-2 sm:grid-cols-3">
            {STARTERS.map((s) => (
              <button
                key={s.label}
                onClick={() => setDraft({ key: Date.now(), text: s.prompt })}
                className="group rounded-[10px] border border-line bg-surface-1 p-3 text-left transition-colors hover:border-line-strong hover:bg-surface-2"
              >
                <span className="flex items-center gap-1.5 text-[12px] text-fg-3 group-hover:text-fg-2">
                  <s.icon className="size-3.5" />
                  {s.label}
                </span>
                <span className="mt-1.5 line-clamp-2 block text-[13px] leading-5 text-fg-2 group-hover:text-fg">{s.prompt}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        ref={scrollRef}
        onScroll={(e) => {
          const el = e.currentTarget;
          stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
        }}
        className="flex-1 overflow-y-auto"
      >
        <div className="mx-auto w-full max-w-[760px] space-y-10 px-4 pb-8 pt-8 sm:px-6">
          {turns.map((t, i) => (
            <TurnView
              key={t.key}
              turn={t}
              canRetry={!running && i === turns.length - 1}
              onRetry={(p) => submit(p, t.mode)}
            />
          ))}
        </div>
      </div>
      <div className="mx-auto w-full max-w-[760px] px-4 pb-4 sm:px-6">{composer(false)}</div>
    </div>
  );
}
