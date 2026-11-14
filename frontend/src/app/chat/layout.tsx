"use client";

import { Suspense, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Menu, Monitor } from "lucide-react";
import Sidebar from "@/components/sidebar";
import BrowserPanel from "@/components/browser-panel";
import { Wordmark } from "@/components/ui";
import { api } from "@/lib/api";
import { useChatStore } from "@/store/chat-store";
import type { Session } from "@/lib/types";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const setSessions = useChatStore((s) => s.setSessions);
  const browserPanelOpen = useChatStore((s) => s.browserPanelOpen);
  const setBrowserPanelOpen = useChatStore((s) => s.setBrowserPanelOpen);
  const hasBrowserTurn = useChatStore((s) => s.focusedTurnKey !== null);

  // Keep the panel mounted after it's closed (from anywhere) until its exit animation ends.
  const [panelMounted, setPanelMounted] = useState(browserPanelOpen);
  if (browserPanelOpen && !panelMounted) setPanelMounted(true);
  const panelExiting = panelMounted && !browserPanelOpen;
  const onPanelAnimationEnd = (e: React.AnimationEvent) => {
    if (e.target === e.currentTarget && panelExiting) setPanelMounted(false);
  };

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    api.get<Session[]>(getToken, "/sessions?limit=100").then(setSessions).catch(() => setSessions([]));
  }, [isLoaded, isSignedIn, getToken, setSessions]);

  return (
    <div className="flex h-dvh overflow-hidden bg-canvas">
      {/* Desktop sidebar */}
      <div className="hidden md:block">
        <Suspense fallback={<div className={`h-full border-r border-line bg-surface-1 ${collapsed ? "w-14" : "w-[264px]"}`} />}>
          <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} onNavigate={() => {}} />
        </Suspense>
      </div>

      {/* Mobile drawer */}
      {mobileNav && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/35" onClick={() => setMobileNav(false)} />
          <div className="absolute inset-y-0 left-0 shadow-[0_12px_40px_rgb(23_23_28/0.14)]">
            <Suspense fallback={null}>
              <Sidebar collapsed={false} onToggle={() => setMobileNav(false)} onNavigate={() => setMobileNav(false)} />
            </Suspense>
          </div>
        </div>
      )}

      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-12 shrink-0 items-center gap-2 border-b border-line px-3 md:hidden">
          <button onClick={() => setMobileNav(true)} className="rounded-md p-1.5 text-fg-2" aria-label="Open tasks">
            <Menu className="size-5" />
          </button>
          <Wordmark />
          {hasBrowserTurn && (
            <button onClick={() => setBrowserPanelOpen(true)} className="ml-auto rounded-md p-1.5 text-fg-2" aria-label="Open browser view">
              <Monitor className="size-5" />
            </button>
          )}
        </div>
        <Suspense fallback={<div className="flex-1" />}>{children}</Suspense>
      </main>

      {/* Browser panel: docked on wide screens, a sheet otherwise */}
      {panelMounted && (
        <>
          <div
            onAnimationEnd={onPanelAnimationEnd}
            className={`hidden w-[44%] min-w-[420px] max-w-[720px] border-l border-line xl:block ${panelExiting ? "panel-out" : "panel-in"}`}
          >
            <BrowserPanel onClose={() => setBrowserPanelOpen(false)} />
          </div>
          <div className={`fixed inset-0 z-40 xl:hidden ${panelExiting ? "pointer-events-none" : ""}`}>
            <div
              className={`absolute inset-0 bg-black/35 ${panelExiting ? "[animation:fade-out-only_220ms_ease_forwards]" : "[animation:fade-only_240ms_ease_backwards]"}`}
              onClick={() => setBrowserPanelOpen(false)}
            />
            <div
              onAnimationEnd={onPanelAnimationEnd}
              className={`absolute inset-y-0 right-0 w-full max-w-[560px] border-l border-line shadow-[0_12px_40px_rgb(23_23_28/0.14)] ${panelExiting ? "panel-out" : "panel-in"}`}
            >
              <BrowserPanel onClose={() => setBrowserPanelOpen(false)} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
