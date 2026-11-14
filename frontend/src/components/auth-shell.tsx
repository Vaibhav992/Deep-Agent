import { Suspense } from "react";
import Link from "next/link";
import { Wordmark } from "./ui";
import { WORDMARK } from "@/lib/brand";

export default function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh bg-canvas lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      {/* Brand side: forest panel with a single quiet statement */}
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-forest p-10 text-white lg:flex">
        <div className="grain pointer-events-none absolute inset-0 opacity-[0.18]" aria-hidden="true" />
        <Link href="/" className="relative flex items-center gap-2">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="1" y="1" width="22" height="22" rx="7" fill="#e5f4ef" />
            <path d="M7 8h10L10 17" stroke="var(--forest)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="font-display text-[17px] leading-none tracking-[-0.04em]">{WORDMARK}</span>
        </Link>
        <div className="relative max-w-[440px]">
          <p className="eyebrow text-[#e5f4ef]/70">Research · Browse · Answer</p>
          <p className="font-display mt-4 text-[40px] leading-[44px] text-balance">An agent you can watch work.</p>
          <p className="mt-4 text-[15px] leading-6 text-white/70">
            Every page it opens and every step it takes, in plain sight.
          </p>
        </div>
        <p className="relative font-mono text-[12px] text-white/45">v0.1</p>
      </aside>

      <div className="flex flex-col">
        <header className="px-6 py-5 lg:hidden">
          <Link href="/"><Wordmark /></Link>
        </header>
        <main className="flex flex-1 items-center justify-center px-4 py-10">
          {/* Clerk's forms read the URL at runtime; the boundary lets the shell prerender. */}
          <Suspense fallback={<div className="skeleton h-[420px] w-[380px] rounded-[18px]" />}>{children}</Suspense>
        </main>
      </div>
    </div>
  );
}
