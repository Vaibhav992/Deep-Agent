"use client";

import { useRef } from "react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { ArrowRight } from "lucide-react";
import { Wordmark } from "@/components/ui";
import HeroReplay from "@/components/landing/hero-replay";
import FeatureStack from "@/components/landing/feature-stack";
import MakerSection, { LinkedInIcon, MAKER, MakerAvatar } from "@/components/landing/maker";
import { EASE_OUT, FULL_MOTION, SplitText, gsap, useGSAP } from "@/lib/gsap";
import { APP_NAME, TAGLINE } from "@/lib/brand";
import ThemeToggle from "@/components/theme-toggle";

// What the agent actually runs on today; no invented customer logos.
const STACK = ["DeepSeek", "BrowserBase", "Exa search", "LangGraph", "Neon Postgres", "Clerk"];

export default function LandingPage() {
  const { isSignedIn } = useAuth();
  const cta = isSignedIn ? "/chat" : "/sign-up";
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const q = gsap.utils.selector(root);
      const mm = gsap.matchMedia();
      mm.add(FULL_MOTION, () => {
        // Headline lines rise from behind a mask; autoSplit re-splits once the web font has loaded.
        SplitText.create(q("[data-headline]"), {
          type: "lines",
          mask: "lines",
          autoSplit: true,
          onSplit: (self) => gsap.from(self.lines, { yPercent: 105, duration: 1, ease: "expo.out", stagger: 0.09 }),
        });
        gsap.from(q("[data-intro]"), { autoAlpha: 0, y: 10, duration: 0.7, ease: EASE_OUT, stagger: 0.08, delay: 0.35 });
        gsap.from(q("[data-hero-media]"), { autoAlpha: 0, y: 28, duration: 1, ease: EASE_OUT, delay: 0.45 });
        // The hero art drifts slightly slower than the page as you scroll past it.
        gsap.to(q("[data-hero-field]"), {
          yPercent: 8,
          ease: "none",
          scrollTrigger: { trigger: q("[data-hero-media]")[0], start: "top bottom", end: "bottom top", scrub: true },
        });
        gsap.from(q("[data-reveal-up]"), {
          autoAlpha: 0,
          y: 20,
          duration: 0.8,
          ease: EASE_OUT,
          stagger: 0.1,
          scrollTrigger: { trigger: q("[data-closing]")[0], start: "top 75%", once: true },
        });
      });
      return () => mm.revert();
    },
    { scope: root },
  );

  return (
    <div ref={root} className="min-h-dvh bg-canvas">
      <header className="sticky top-0 z-30 border-b border-line bg-canvas/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1280px] items-center gap-8 px-6">
          <Link href="/"><Wordmark /></Link>
          <nav className="hidden items-center gap-7 text-[14px] text-fg-2 md:flex">
            <a href="#product" className="transition-colors hover:text-fg">Product</a>
            <a href="#how" className="transition-colors hover:text-fg">How it works</a>
            <a href="#safety" className="transition-colors hover:text-fg">Safety</a>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle className="mr-1" />
            {!isSignedIn && (
              <Link href="/sign-in" className="px-3 py-2 text-[14px] text-fg-2 transition-colors hover:text-fg">
                Sign in
              </Link>
            )}
            <Link href={cta} className="btn-ink press px-4 py-2 text-[14px]">
              {isSignedIn ? "Open workspace" : "Start a task"}
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-[1280px] px-6 pb-10 pt-20 text-center sm:pt-28">
          <p data-intro className="eyebrow text-fg-3">Research · Browse · Answer</p>
          <h1
            data-headline
            className="font-display mx-auto mt-6 max-w-[980px] text-[46px] leading-[1.02] text-balance sm:text-[76px] lg:text-[96px]"
          >
            An agent you can watch work.
          </h1>
          <p data-intro className="mx-auto mt-7 max-w-[560px] text-[17px] leading-[27px] text-pretty text-fg-2">
            Give {APP_NAME} a task. It plans, searches the web and works in a real browser, showing you every step, then
            answers with sources you can check.
          </p>
          <div data-intro className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link href={cta} className="btn-ink press px-6 py-3 text-[15px]">
              {isSignedIn ? "Open the workspace" : "Start a task"}
              <ArrowRight className="size-4" />
            </Link>
            <a href="#how" className="btn-ghost press px-6 py-3 text-[15px]">
              See how it works
            </a>
          </div>
        </section>

        <section id="product" className="mx-auto max-w-[1280px] px-4 sm:px-6">
          <div data-hero-media className="relative overflow-hidden rounded-[24px]">
            <div data-hero-field className="field-forest absolute -inset-y-[10%] inset-x-0" aria-hidden="true" />
            <div className="grain pointer-events-none absolute inset-0 opacity-30" aria-hidden="true" />
            <div className="relative px-3 pb-3 pt-10 sm:px-10 sm:pb-12 sm:pt-16 lg:px-20 lg:pt-20">
              <HeroReplay />
            </div>
          </div>
        </section>

        {/* What it runs on */}
        <section className="mx-auto max-w-[1280px] px-6 py-20 text-center">
          <p className="text-[15px] text-fg-2">Built on infrastructure you already trust</p>
          <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-12 gap-y-4">
            {STACK.map((s) => (
              <li key={s} className="font-display text-[20px] tracking-[-0.03em] text-fg-3">{s}</li>
            ))}
          </ul>
        </section>

        {/* Capabilities: stacking panels */}
        <section id="how" className="bg-cream py-24 sm:py-32">
          <div className="mx-auto max-w-[1280px] px-4 sm:px-6">
            <div className="mx-auto mb-14 max-w-[720px] text-center">
              <p className="eyebrow text-fg-3">How it works</p>
              <h2 className="mt-5 text-[34px] font-normal leading-[40px] tracking-[-0.02em] text-balance sm:text-[52px] sm:leading-[58px]">
                Three things it does, all of them visible.
              </h2>
            </div>
            <div id="safety">
              <FeatureStack cta={cta} />
            </div>
          </div>
        </section>

        <MakerSection />

        {/* Closing */}
        <section data-closing className="relative overflow-hidden">
          <div className="field-forest absolute inset-0" aria-hidden="true" />
          <div className="grain pointer-events-none absolute inset-0 opacity-30" aria-hidden="true" />
          <div className="relative mx-auto flex max-w-[1280px] flex-col items-center px-6 py-32 text-center text-white sm:py-44">
            <h2 data-reveal-up className="font-display max-w-[760px] text-[44px] leading-[1.04] text-balance sm:text-[72px]">
              Give it a task.
            </h2>
            <p data-reveal-up className="mt-6 max-w-[460px] text-[17px] leading-[27px] text-white/75">
              Watch it plan, browse and answer, then check every source yourself.
            </p>
            <div data-reveal-up className="mt-10">
              <Link href={cta} className="btn-ink press !bg-white px-6 py-3 text-[15px] !text-[#17171c] hover:!bg-white/90">
                {isSignedIn ? "Open the workspace" : "Start a task"}
                <ArrowRight className="size-4" />
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-night text-white/60">
        <div className="mx-auto flex max-w-[1280px] flex-col gap-10 px-6 py-14 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <span className="text-white">
              <Wordmark tone="onDark" />
            </span>
            <p className="mt-4 max-w-[280px] text-[13px] leading-5">
              {TAGLINE} <span className="text-white/40">ध्यानिक · of deep attention.</span>
            </p>
          </div>
          <nav className="grid grid-cols-2 gap-x-16 gap-y-2 text-[14px]">
            <a href="#product" className="hover:text-white">Product</a>
            <Link href="/sign-in" className="hover:text-white">Sign in</Link>
            <a href="#how" className="hover:text-white">How it works</a>
            <Link href={cta} className="hover:text-white">Start a task</Link>
            <a href="#safety" className="hover:text-white">Safety</a>
          </nav>
        </div>
        <div className="mx-auto flex max-w-[1280px] flex-col gap-4 border-t border-white/10 px-6 py-6 sm:flex-row sm:items-center sm:justify-between">
          <a
            href={MAKER.linkedin}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-3 text-[13px] transition-colors hover:text-white"
          >
            <MakerAvatar size={28} ring={false} />
            <span>
              Developed by <span className="text-white">{MAKER.name}</span>
            </span>
            <LinkedInIcon className="size-3.5 opacity-60 transition-opacity group-hover:opacity-100" />
          </a>
          <span className="font-mono text-[12px]">v0.1</span>
        </div>
      </footer>
    </div>
  );
}
