import { Suspense } from "react";
import Link from "next/link";
import { Wordmark } from "./ui";

export default function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-dvh flex-col bg-canvas">
      <div
        className="pointer-events-none absolute left-1/2 top-1/4 h-[360px] w-[560px] -translate-x-1/2 rounded-full opacity-60 blur-[100px]"
        style={{ background: "radial-gradient(closest-side, #1e2a12, transparent)" }}
        aria-hidden="true"
      />
      <header className="relative px-6 py-5">
        <Link href="/"><Wordmark /></Link>
      </header>
      <main className="relative flex flex-1 items-center justify-center px-4 pb-16">
        {/* Clerk's forms read the URL at runtime; the boundary lets the shell prerender. */}
        <Suspense fallback={<div className="skeleton h-[420px] w-[380px] rounded-[14px]" />}>{children}</Suspense>
      </main>
    </div>
  );
}
