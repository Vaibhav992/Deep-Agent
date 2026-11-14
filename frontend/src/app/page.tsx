"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { ArrowRight, Globe, ListChecks, ShieldCheck } from "lucide-react";
import { Wordmark } from "@/components/ui";

const CAPABILITIES = [
  {
    icon: ListChecks,
    title: "Plans, then researches",
    body: "Breaks a question into steps, searches the web for each one, and writes an answer from what it found.",
  },
  {
    icon: Globe,
    title: "Works in a real browser",
    body: "Opens sites, clicks, types and reads pages. You watch every page it visits, screenshot by screenshot.",
  },
  {
    icon: ShieldCheck,
    title: "Guarded by default",
    body: "Inputs and answers pass through safety checks, and the browser can't reach private or internal addresses.",
  },
];

export default function LandingPage() {
  const { isSignedIn } = useAuth();
  const cta = isSignedIn ? "/chat" : "/sign-up";

  return (
    <div className="min-h-dvh bg-canvas">
      <header className="mx-auto flex h-16 max-w-[1080px] items-center justify-between px-6">
        <Wordmark />
        <nav className="flex items-center gap-2">
          {!isSignedIn && (
            <Link href="/sign-in" className="rounded-lg px-3 py-1.5 text-[13px] text-fg-2 transition-colors hover:text-fg">
              Sign in
            </Link>
          )}
          <Link href={cta} className="rounded-lg bg-signal px-3 py-1.5 text-[13px] font-medium text-signal-ink">
            {isSignedIn ? "Open app" : "Get started"}
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-[1080px] px-6">
        <section className="relative pb-20 pt-24 sm:pt-32">
          <div
            className="pointer-events-none absolute -left-20 top-10 h-[420px] w-[560px] rounded-full opacity-70 blur-[100px]"
            style={{ background: "radial-gradient(closest-side, #1e2a12, transparent)" }}
            aria-hidden="true"
          />
          <div className="relative max-w-[640px]">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-line px-3 py-1 font-mono text-[12px] text-fg-2">
              <span className="size-1.5 rounded-full bg-signal" />
              research · browse · answer
            </p>
            <h1 className="text-[40px] font-semibold leading-[1.08] tracking-[-0.03em] sm:text-[56px]">
              An agent you can
              <br />
              watch work.
            </h1>
            <p className="mt-5 max-w-[520px] text-[16px] leading-[26px] text-fg-2">
              Give Deep Agent a task. It plans, searches the web, operates a real browser, and shows you each step
              as it happens, then gives you an answer you can check.
            </p>
            <div className="mt-8 flex items-center gap-3">
              <Link href={cta} className="flex items-center gap-2 rounded-lg bg-signal px-4 py-2.5 text-[14px] font-medium text-signal-ink">
                {isSignedIn ? "Open the workspace" : "Start a task"}
                <ArrowRight className="size-4" />
              </Link>
            </div>
          </div>
        </section>

        <section className="grid gap-px overflow-hidden rounded-[14px] border border-line bg-line sm:grid-cols-3">
          {CAPABILITIES.map((c) => (
            <div key={c.title} className="bg-surface-1 p-6">
              <c.icon className="size-5 text-fg-2" />
              <h2 className="mt-4 text-[15px] font-medium">{c.title}</h2>
              <p className="mt-1.5 text-[13px] leading-[21px] text-fg-2">{c.body}</p>
            </div>
          ))}
        </section>

        <footer className="flex items-center justify-between py-10 text-[12px] text-fg-3">
          <span>Deep Agent</span>
          <span className="font-mono">v0.1</span>
        </footer>
      </main>
    </div>
  );
}
