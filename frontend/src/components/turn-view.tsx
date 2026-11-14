"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertTriangle, Check, Copy, RotateCcw, ShieldAlert } from "lucide-react";
import { useChatStore } from "@/store/chat-store";
import type { Turn } from "@/lib/types";
import RunCard from "./run-card";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="press flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] text-fg-3 hover:bg-surface-2 hover:text-fg"
    >
      {copied ? <Check className="size-3.5 swap-in" /> : <Copy className="size-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default function TurnView({
  turn,
  onRetry,
  canRetry,
}: {
  turn: Turn;
  onRetry: (prompt: string) => void;
  canRetry: boolean;
}) {
  const { run } = turn;
  const focusedTurnKey = useChatStore((s) => s.focusedTurnKey);
  const browserPanelOpen = useChatStore((s) => s.browserPanelOpen);
  const focusBrowser = useChatStore((s) => s.focusBrowser);
  const focused = focusedTurnKey === turn.key && browserPanelOpen;

  return (
    <article className="space-y-3">
      <div className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-[18px] rounded-br-md bg-cream px-4 py-2.5 text-[14px] leading-[22px] text-fg">
          {turn.prompt}
        </p>
      </div>

      <RunCard run={run} browserFocused={focused} onShowBrowser={() => focusBrowser(focused ? null : turn.key)} />

      {run.blockedReason && (
        <div className="flex items-start gap-2.5 rounded-[10px] border border-warn/25 bg-warn-wash px-3.5 py-3 text-[13px] text-fg" role="status">
          <ShieldAlert className="mt-0.5 size-4 shrink-0 text-warn" />
          <span>Blocked by the safety filter. {run.blockedReason}</span>
        </div>
      )}

      {run.answer && (
        <div className="enter">
          <div className="prose-answer">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{ a: (props) => <a {...props} target="_blank" rel="noopener noreferrer" /> }}
            >
              {run.answer}
            </ReactMarkdown>
          </div>
          {run.status !== "running" && (
            <div className="mt-2 flex items-center gap-1">
              <CopyButton text={run.answer} />
              {run.model && <span className="ml-1 font-mono text-[11px] text-fg-3">{run.model}</span>}
            </div>
          )}
        </div>
      )}

      {run.error && (
        <div className="flex items-start gap-2.5 rounded-[10px] border border-danger/25 bg-danger-wash px-3.5 py-3 text-[13px]" role="alert">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-danger" />
          <span className="flex-1 text-fg">{run.error}</span>
          {canRetry && (
            <button onClick={() => onRetry(turn.prompt)} className="press flex items-center gap-1.5 rounded-md px-2 py-0.5 text-fg-2 hover:bg-surface-3 hover:text-fg">
              <RotateCcw className="size-3.5" />
              Retry
            </button>
          )}
        </div>
      )}

      {run.status === "cancelled" && !run.answer && (
        <div className="flex items-center gap-2 text-[13px] text-fg-3">
          <span>Stopped before finishing.</span>
          {canRetry && (
            <button onClick={() => onRetry(turn.prompt)} className="press flex items-center gap-1 rounded-md px-1.5 py-0.5 text-fg-2 hover:bg-surface-2 hover:text-fg">
              <RotateCcw className="size-3.5" />
              Run again
            </button>
          )}
        </div>
      )}
    </article>
  );
}
