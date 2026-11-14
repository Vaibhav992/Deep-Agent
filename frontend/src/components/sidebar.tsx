"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useAuth, UserButton } from "@clerk/nextjs";
import { PanelLeftClose, PanelLeftOpen, Plus, Search, Settings, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";
import ConfirmDialog from "./confirm-dialog";
import { useActiveRun } from "@/lib/runner";
import { useChatStore } from "@/store/chat-store";
import type { Session } from "@/lib/types";
import { Logo, StatusDot, Wordmark, useClientNow } from "./ui";
import { APP_NAME } from "@/lib/brand";
import ThemeToggle from "./theme-toggle";

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
  const [pendingDelete, setPendingDelete] = useState<Session | null>(null);
  const [deleting, setDeleting] = useState(false);

  const now = useClientNow();
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    return groupSessions(q ? sessions.filter((s) => s.title.toLowerCase().includes(q)) : sessions, now);
  }, [sessions, query, now]);

  function askDelete(s: Session) {
    if (running?.sessionId === s.id) {
      toast.info("This task is still running", { description: "Stop it first, then delete it." });
      return;
    }
    setPendingDelete(s);
  }

  async function confirmDelete() {
    const s = pendingDelete;
    if (!s) return;
    setDeleting(true);
    const title = s.title || "Untitled task";
    try {
      await api.delete(getToken, `/sessions/${s.id}`);
      removeSession(s.id);
      setPendingDelete(null);
      if (s.id === activeId) router.push("/chat");
      toast.success("Task deleted", { description: title });
    } catch (e) {
      setPendingDelete(null);
      const notFound = e instanceof ApiError && e.status === 404;
      if (notFound) {
        // Already gone on the server (e.g. deleted in another tab): reflect that locally.
        removeSession(s.id);
        toast.info("Task was already deleted", { description: title });
      } else {
        toast.error("Couldn't delete task", {
          description: "Something went wrong on our side. Please try again.",
          action: { label: "Try again", onClick: () => setPendingDelete(s) },
        });
      }
    } finally {
      setDeleting(false);
    }
  }

  if (collapsed) {
    return (
      <nav className="flex h-full w-14 flex-col items-center gap-2 border-r border-line bg-surface-1 py-3" aria-label="Tasks">
        <Link href="/chat" className="mb-2 rounded-md p-1" aria-label={`${APP_NAME} home`}><Logo /></Link>
        <button onClick={onToggle} className="rounded-md p-2 text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg" aria-label="Expand sidebar">
          <PanelLeftOpen className="size-4" />
        </button>
        <Link href="/chat" className="rounded-md p-2 text-fg-3 transition-colors hover:bg-surface-2 hover:text-fg" aria-label="New task">
          <Plus className="size-4" />
        </Link>
        <div className="mt-auto flex flex-col items-center gap-2">
          <ThemeToggle />
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
          className="press btn-ink h-9 px-4 text-[13px] transition-colors hover:border-line-strong"
        >
          <Plus className="size-4" />
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
        {groups.map((g) => (
          <section key={g.label} className="pt-4">
            <h3 className="eyebrow px-3 pb-1 text-fg-3">{g.label}</h3>
            <ul>
              {g.items.map((s) => {
                const active = s.id === activeId;
                const isRunning = running?.sessionId === s.id;
                return (
                  <li key={s.id} className="group relative">
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
                          onClick={() => askDelete(s)}
                          className={`absolute right-1.5 top-1.5 rounded p-1 text-fg-3 transition-opacity hover:text-danger focus-visible:opacity-100 group-hover:opacity-100 ${
                            pendingDelete?.id === s.id ? "opacity-100" : "opacity-0 [@media(hover:none)]:opacity-100"
                          }`}
                          aria-label={`Delete ${s.title}`}
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete this task?"
        description={
          <>
            <span className="font-medium text-fg">&ldquo;{pendingDelete?.title || "Untitled task"}&rdquo;</span> and its
            whole conversation will be permanently deleted. Saved memories are kept. This can&apos;t be undone.
          </>
        }
        confirmLabel={deleting ? "Deleting…" : "Delete task"}
        destructive
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />

      <div className="flex items-center gap-2 border-t border-line px-3 py-3">
        <UserButton />
        <ThemeToggle className="ml-1" />
        <Link href="/settings" className="ml-auto flex items-center gap-1.5 rounded-md px-2 py-1.5 text-[13px] text-fg-2 transition-colors hover:bg-surface-2 hover:text-fg">
          <Settings className="size-4" />
          Settings
        </Link>
      </div>
    </nav>
  );
}
