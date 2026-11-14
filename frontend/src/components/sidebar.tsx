"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useAuth, UserButton } from "@clerk/nextjs";
import { PanelLeftClose, PanelLeftOpen, Plus, Search, Settings, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";
import { useActiveRun } from "@/lib/runner";
import { useChatStore } from "@/store/chat-store";
import type { Session } from "@/lib/types";
import { Logo, StatusDot, Wordmark, useClientNow } from "./ui";

function groupSessions(sessions: Session[], now: Date | null) {
  if (!now) return [];
  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);
  const day = 86_400_000;
  const groups: { label: string; items: Session[] }[] = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Previous 7 days", items: [] },
    { label: "Older", items: [] },
  ];
  for (const s of sessions) {
    const t = new Date(s.updated_at).getTime();
    const i = t >= startOfToday.getTime() ? 0 : t >= startOfToday.getTime() - day ? 1 : t >= startOfToday.getTime() - 7 * day ? 2 : 3;
    groups[i].items.push(s);
  }
  return groups.filter((g) => g.items.length);
}

export default function Sidebar({
  collapsed,
  onToggle,
  onNavigate,
}: {
  collapsed: boolean;
  onToggle: () => void;
  onNavigate: () => void;
}) {
  const { getToken } = useAuth();
  const router = useRouter();
  const params = useParams<{ sessionId?: string }>();
  const activeId = params.sessionId ?? null;
  const { sessions, sessionsLoaded, removeSession } = useChatStore();
  const running = useActiveRun((s) => s.active);
  const [query, setQuery] = useState("");
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const now = useClientNow();
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    return groupSessions(q ? sessions.filter((s) => s.title.toLowerCase().includes(q)) : sessions, now);
  }, [sessions, query, now]);

  async function deleteSession(id: string) {
    setDeleteError(null);
    try {
      await api.delete(getToken, `/sessions/${id}`);
      removeSession(id);
      setConfirmId(null);
      if (id === activeId) router.push("/chat");
    } catch {
      setDeleteError("Couldn't delete that task. Try again.");
    }
  }

  if (collapsed) {
    return (
      <nav className="flex h-full w-14 flex-col items-center gap-2 border-r border-line bg-surface-1 py-3" aria-label="Tasks">
        <Link href="/chat" className="mb-2 rounded-md p-1" aria-label="Deep Agent home"><Logo /></Link>
        <button onClick={onToggle} className="rounded-md p-2 text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg" aria-label="Expand sidebar">
          <PanelLeftOpen className="size-4" />
        </button>
        <Link href="/chat" className="rounded-md p-2 text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg" aria-label="New task">
          <Plus className="size-4" />
        </Link>
        <div className="mt-auto flex flex-col items-center gap-2">
          <Link href="/settings" className="rounded-md p-2 text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg" aria-label="Settings">
            <Settings className="size-4" />
          </Link>
          <UserButton />
        </div>
      </nav>
    );
  }

  return (
    <nav className="flex h-full w-[264px] flex-col border-r border-line bg-surface-1" aria-label="Tasks">
      <div className="flex h-14 items-center justify-between px-4">
        <Link href="/chat" onClick={onNavigate}><Wordmark /></Link>
        <button onClick={onToggle} className="rounded-md p-1.5 text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg" aria-label="Collapse sidebar">
          <PanelLeftClose className="size-4" />
        </button>
      </div>

      <div className="space-y-2 px-3">
        <Link
          href="/chat"
          onClick={onNavigate}
          className="flex h-9 items-center gap-2 rounded-lg border border-line bg-surface-2 px-3 text-[13px] text-fg transition-colors hover:border-line-strong"
        >
          <Plus className="size-4 text-fg-2" />
          New task
        </Link>
        <label className="flex h-9 items-center gap-2 rounded-lg px-3 text-fg-3 focus-within:bg-surface-2">
          <Search className="size-3.5 shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search tasks"
            className="w-full bg-transparent text-[13px] text-fg placeholder:text-fg-3 focus:outline-none"
            aria-label="Search tasks"
          />
        </label>
      </div>

      <div className="mt-2 flex-1 overflow-y-auto px-2 pb-4">
        {!sessionsLoaded && (
          <div className="space-y-2 px-2 pt-3">
            {[70, 55, 80, 45].map((w) => <div key={w} className="skeleton h-4 rounded" style={{ width: `${w}%` }} />)}
          </div>
        )}
        {sessionsLoaded && sessions.length === 0 && (
          <p className="px-3 pt-4 text-[13px] text-fg-3">Your tasks will appear here.</p>
        )}
        {sessionsLoaded && sessions.length > 0 && groups.length === 0 && (
          <p className="px-3 pt-4 text-[13px] text-fg-3">No tasks match “{query}”.</p>
        )}
        {deleteError && <p className="px-3 pt-2 text-[12px] text-danger" role="alert">{deleteError}</p>}
        {groups.map((g) => (
          <section key={g.label} className="pt-4">
            <h3 className="px-3 pb-1 text-[11px] font-medium uppercase tracking-[0.06em] text-fg-3">{g.label}</h3>
            <ul>
              {g.items.map((s) => {
                const active = s.id === activeId;
                const isRunning = running?.sessionId === s.id;
                return (
                  <li key={s.id} className="group relative">
                    {confirmId === s.id ? (
                      <div className="flex h-8 items-center gap-1 rounded-md bg-danger-wash px-3 text-[13px]">
                        <span className="flex-1 truncate text-fg">Delete this task?</span>
                        <button onClick={() => deleteSession(s.id)} className="rounded px-1.5 text-danger hover:underline">Delete</button>
                        <button onClick={() => setConfirmId(null)} className="rounded p-1 text-fg-3 hover:text-fg" aria-label="Cancel delete">
                          <X className="size-3.5" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <Link
                          href={`/chat/${s.id}`}
                          onClick={onNavigate}
                          className={`flex h-8 items-center gap-2 rounded-md pl-3 pr-8 text-[13px] transition-colors ${
                            active ? "bg-surface-3 text-fg" : "text-fg-2 hover:bg-surface-2 hover:text-fg"
                          }`}
                          aria-current={active ? "page" : undefined}
                        >
                          {isRunning && <StatusDot status="running" />}
                          <span className="truncate">{s.title || "Untitled task"}</span>
                        </Link>
                        <button
                          onClick={() => setConfirmId(s.id)}
                          className="absolute right-1.5 top-1.5 rounded p-1 text-fg-3 opacity-0 transition-opacity hover:text-danger focus:opacity-100 group-hover:opacity-100"
                          aria-label={`Delete ${s.title}`}
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>

      <div className="flex items-center gap-2 border-t border-line px-3 py-3">
        <UserButton />
        <Link href="/settings" className="ml-auto flex items-center gap-1.5 rounded-md px-2 py-1.5 text-[13px] text-fg-2 transition-colors hover:bg-surface-2 hover:text-fg">
          <Settings className="size-4" />
          Settings
        </Link>
      </div>
    </nav>
  );
}
