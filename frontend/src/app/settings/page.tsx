"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { useUser, UserProfile, SignOutButton } from "@clerk/nextjs";
import { ArrowLeft, Check, LogOut } from "lucide-react";
import { api } from "@/lib/api";
import type { LLMModel } from "@/lib/types";
import ThemeToggle from "@/components/theme-toggle";

const MODEL_KEY = "deep-agent:model";
const modelListeners = new Set<() => void>();

function readModel(): string {
  try {
    return window.localStorage.getItem(MODEL_KEY) ?? "";
  } catch {
    return "";
  }
}

function subscribeModel(cb: () => void) {
  modelListeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    modelListeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

export default function SettingsPage() {
  const { user } = useUser();
  const [models, setModels] = useState<LLMModel[] | null>(null);
  const [error, setError] = useState(false);
  const selected = useSyncExternalStore(subscribeModel, readModel, () => "");
  const [showAccount, setShowAccount] = useState(false);

  useEffect(() => {
    api
      .get<LLMModel[]>(async () => null, "/models")
      .then((m) => setModels(m.filter((x) => x.supports_tools)))
      .catch(() => setError(true));
  }, []);

  function choose(id: string) {
    try {
      if (id) window.localStorage.setItem(MODEL_KEY, id);
      else window.localStorage.removeItem(MODEL_KEY);
    } catch {
      // Storage unavailable (private mode): the choice won't persist.
    }
    modelListeners.forEach((l) => l());
  }

  return (
    <div className="min-h-dvh bg-canvas">
      <header className="mx-auto flex h-14 max-w-[720px] items-center px-6">
        <Link href="/chat" className="flex items-center gap-1.5 text-[13px] text-fg-2 transition-colors hover:text-fg">
          <ArrowLeft className="size-4" />
          Back to workspace
        </Link>
      </header>

      <main className="mx-auto max-w-[720px] space-y-10 px-6 pb-16 pt-6">
        <div>
          <h1 className="text-[20px] font-medium tracking-[-0.01em]">Settings</h1>
          <p className="mt-1 text-[13px] text-fg-2">Signed in as {user?.primaryEmailAddress?.emailAddress ?? "…"}</p>
        </div>

        <section>
          <h2 className="text-[14px] font-medium">Model</h2>
          <p className="mt-1 text-[13px] text-fg-2">
            Used for new tasks on this device. &ldquo;Automatic&rdquo; picks a fast model for routing and tool use and a
            reasoning model for planning and writing.
          </p>
          <div className="mt-4 overflow-hidden rounded-[10px] border border-line" role="radiogroup" aria-label="Model">
            {error && <p className="px-4 py-3 text-[13px] text-danger">Couldn&apos;t load models from the agent server.</p>}
            {!error && models === null && (
              <div className="space-y-2 p-4">
                <div className="skeleton h-4 w-1/2 rounded" />
                <div className="skeleton h-4 w-1/3 rounded" />
              </div>
            )}
            {models && (
              <>
                <ModelRow id="" name="Automatic" detail="Recommended" selected={selected === ""} onSelect={choose} />
                {models.map((m) => (
                  <ModelRow
                    key={m.id}
                    id={m.id}
                    name={m.display_name}
                    detail={`${m.provider} · ${Math.round(m.context_window / 1000)}k context · $${m.input_cost_per_1m}/$${m.output_cost_per_1m} per 1M tokens`}
                    selected={selected === m.id}
                    onSelect={choose}
                  />
                ))}
              </>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-[14px] font-medium">Appearance</h2>
          <div className="mt-4 flex items-center justify-between rounded-[14px] border border-line px-4 py-3">
            <div>
              <p className="text-[13px] text-fg">Dark mode</p>
              <p className="text-[12px] text-fg-3">Follows your system until you choose. Saved on this device.</p>
            </div>
            <ThemeToggle />
          </div>
        </section>

        <section>
          <h2 className="text-[14px] font-medium">Account</h2>
          <p className="mt-1 text-[13px] text-fg-2">Profile, email, password and connected accounts are managed by Clerk.</p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              onClick={() => setShowAccount((s) => !s)}
              className="rounded-lg border border-line bg-surface-2 px-3 py-1.5 text-[13px] text-fg transition-colors hover:border-line-strong"
            >
              {showAccount ? "Hide account settings" : "Manage account"}
            </button>
            <SignOutButton redirectUrl="/">
              <button className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-[13px] text-fg-2 transition-colors hover:border-danger hover:text-danger">
                <LogOut className="size-3.5" />
                Sign out
              </button>
            </SignOutButton>
          </div>
          {showAccount && (
            <div className="mt-4">
              <UserProfile routing="hash" />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function ModelRow({
  id, name, detail, selected, onSelect,
}: { id: string; name: string; detail: string; selected: boolean; onSelect: (id: string) => void }) {
  return (
    <button
      role="radio"
      aria-checked={selected}
      onClick={() => onSelect(id)}
      className={`flex w-full items-center gap-3 border-b border-line px-4 py-3 text-left transition-colors last:border-b-0 ${
        selected ? "bg-surface-2" : "hover:bg-surface-1"
      }`}
    >
      <span className={`flex size-4 shrink-0 items-center justify-center rounded-full border ${selected ? "border-ink bg-ink" : "border-line-strong"}`}>
        {selected && <Check className="size-2.5 text-on-ink" strokeWidth={3} />}
      </span>
      <span className="min-w-0">
        <span className="block text-[13px] text-fg">{name}</span>
        <span className="block truncate font-mono text-[11.5px] text-fg-3">{detail}</span>
      </span>
    </button>
  );
}
