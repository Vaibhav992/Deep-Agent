import { Suspense } from "react";
import Link from "next/link";
import { Wordmark } from "./ui";

export default function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh bg-canvas lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      {/* Brand side: forest panel with a single quiet statement */}
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-forest p-10 text-white lg:flex">
        <div className="grain pointer-events-none absolute inset-0 opacity-[0.18]" aria-hidden="true" />
        <Link href="/" className="relative">
          <Wordmark tone="onDark" />
        </Link>
        <div className="relative max-w-[440px]">
          <p className="eyebrow text-[#e5f4ef]/70">ध्यानिक · of deep attention</p>
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
