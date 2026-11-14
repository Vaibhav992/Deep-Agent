"use client";

import { useRef } from "react";
import { ArrowUp, Check, FileText, Globe, Lock, Monitor } from "lucide-react";
import { EASE_OUT, FULL_MOTION, REDUCED_MOTION, ScrollTrigger, gsap, useGSAP } from "@/lib/gsap";
import { APP_NAME, WORDMARK } from "@/lib/brand";

// A recorded run (exported from the database: public/demo/hn-run.json + hn-frame.jpg), replayed at ~4x speed.
const PROMPT = "Open https://news.ycombinator.com and summarise the top 5 stories with their links.";
const ACTIONS = [
  { icon: Globe, text: "Opened news.ycombinator.com", secs: "10.3s" },
  { icon: FileText, text: "Read the page text", secs: "3.0s" },
  { icon: FileText, text: "Collected the page's links", secs: "3.0s" },
];
const ANSWER = [
  "Why get an expensive Pi when I have an old phone?",
  "Ggml v1.0.0",
  "Monkey Island: all 13 versions side by side",
];

export default function HeroReplay() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const q = gsap.utils.selector(root);
      const mm = gsap.matchMedia();

      mm.add(REDUCED_MOTION, () => {
        // Show the finished run, no motion.
        gsap.set(q("[data-prompt]"), { text: PROMPT });
        gsap.set(q("[data-url]"), { text: "https://news.ycombinator.com/" });
        gsap.set(q("[data-status]"), { text: "Done" });
      });

      mm.add(FULL_MOTION, () => {
        const tl = gsap.timeline({ repeat: -1, repeatDelay: 0.6, defaults: { ease: EASE_OUT } });
        tl.set(q("[data-reveal]"), { autoAlpha: 0, y: 6 })
          .set(q("[data-frame]"), { clipPath: "inset(0% 0% 100% 0%)" })
          .set(q("[data-prompt]"), { text: "" })
          .set(q("[data-url]"), { text: "" })
          .set(q("[data-status]"), { text: "Thinking" })
          .set(q("[data-dot]"), { attr: { class: "inline-block size-1.5 rounded-full bg-signal live-dot" } })
          .set(q("[data-check]"), { autoAlpha: 0, scale: 0.9 })
          // 1. The prompt types itself, then Send is pressed.
          .to(q("[data-prompt]"), { text: PROMPT, duration: 1.6, ease: "none" })
          .to(q("[data-send]"), { scale: 0.92, duration: 0.08, ease: "power1.out" }, "+=0.15")
          .to(q("[data-send]"), { scale: 1, duration: 0.18 })
          // 2. The run card appears and the agent starts browsing.
          .to(q("[data-card]"), { autoAlpha: 1, y: 0, duration: 0.3 }, "<")
          .set(q("[data-status]"), { text: "Browsing" }, "+=0.35");

        // 3. Each real action lands; the first one loads the page in the browser view.
        ACTIONS.forEach((_, i) => {
          tl.to(q(`[data-row="${i}"]`), { autoAlpha: 1, y: 0, duration: 0.25 }, i === 0 ? "+=0.1" : "+=0.55");
          if (i === 0) {
            tl.to(q("[data-url]"), { text: "https://news.ycombinator.com/", duration: 0.5, ease: "none" }, "<+=0.1")
              .to(q("[data-frame]"), { clipPath: "inset(0% 0% 0% 0%)", duration: 0.7, ease: "power3.inOut" }, "<+=0.2");
          }
          tl.to(q(`[data-row="${i}"] [data-check]`), { autoAlpha: 1, scale: 1, duration: 0.18 }, "+=0.45");
        });

        // 4. The answer arrives; the run settles.
        tl.set(q("[data-status]"), { text: "Done" }, "+=0.3")
          .set(q("[data-dot]"), { attr: { class: "inline-block size-1.5 rounded-full bg-fg-3" } }, "<")
          .to(q("[data-summary]"), { autoAlpha: 1, y: 0, duration: 0.2 }, "<")
          .to(q("[data-answer]"), { autoAlpha: 1, y: 0, duration: 0.3, stagger: 0.09 }, "<")
          .to({}, { duration: 3.2 })
          .to(q("[data-reveal]"), { autoAlpha: 0, duration: 0.35, ease: "power1.in" })
          .to(q("[data-frame]"), { autoAlpha: 0, duration: 0.35, ease: "power1.in" }, "<")
          .set(q("[data-frame]"), { autoAlpha: 1, clipPath: "inset(0% 0% 100% 0%)" });

        // Only play while the hero is on screen.
        ScrollTrigger.create({
          trigger: root.current,
          start: "top bottom",
          end: "bottom top",
          onToggle: (self) => (self.isActive ? tl.play() : tl.pause()),
        });
      });

      return () => mm.revert();
    },
    { scope: root },
  );

  return (
    <div
      ref={root}
      className="relative overflow-hidden rounded-[16px] bg-canvas text-fg shadow-[0_2px_4px_rgb(0_0_0/0.06),0_24px_60px_rgb(0_0_0/0.28)]"
      aria-label={`Replay of a real ${APP_NAME} run on Hacker News`}
    >
      <div className="flex items-center gap-2 border-b border-line bg-surface-1 px-4 py-2.5">
        <span className="size-2.5 rounded-full bg-surface-3" />
        <span className="size-2.5 rounded-full bg-surface-3" />
        <span className="size-2.5 rounded-full bg-surface-3" />
        <span className="eyebrow ml-3 text-fg-3">{WORDMARK} · workspace</span>
        <span className="eyebrow ml-auto hidden text-fg-3 sm:inline">Replay of a real run · ~4× speed</span>
      </div>
      <div className="grid gap-3 p-3 sm:p-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.3fr)]">
        {/* Thread */}
        <div className="flex min-w-0 flex-col gap-3">
          <div className="rounded-[14px] border border-line bg-canvas p-3 shadow-[0_6px_18px_rgb(23_23_28/0.05)]">
            <p data-prompt className="min-h-[44px] text-[13px] leading-[22px] text-fg">{PROMPT}</p>
            <div className="mt-2 flex items-center gap-2">
              <span className="rounded-full bg-surface-2 px-2.5 py-0.5 text-[11px] text-fg-2">Browse</span>
              <span data-send className="btn-ink ml-auto size-7 justify-center">
                <ArrowUp className="size-3.5" strokeWidth={2.5} />
              </span>
            </div>
          </div>

          <div data-reveal data-card className="overflow-hidden rounded-[14px] border border-line bg-canvas">
            <div className="flex items-center gap-2.5 px-3 py-2">
              <span data-dot className="inline-block size-1.5 rounded-full bg-fg-3" />
              <span data-status className="text-[12.5px] text-fg">Done</span>
              <span data-reveal data-summary className="font-mono text-[11px] text-fg-3">· 28s · 3 browser actions</span>
            </div>
            <ul className="space-y-0.5 border-t border-line px-2 py-1.5">
              {ACTIONS.map((a, i) => (
                <li key={a.text} data-reveal data-row={i} className="flex items-center gap-2.5 rounded-md px-1 py-1">
                  <a.icon className="size-3.5 text-fg-3" />
                  <span className="flex-1 truncate text-[12.5px] text-fg-2">{a.text}</span>
                  <span className="font-mono text-[10.5px] text-fg-3">{a.secs}</span>
                  <Check data-check className="size-3.5 text-fg-3" />
                </li>
              ))}
            </ul>
          </div>

          <ol className="space-y-1.5 px-1">
            {ANSWER.map((t, i) => (
              <li key={t} data-reveal data-answer className="flex gap-2 text-[13px] leading-5 text-fg">
                <span className="font-mono text-[11px] leading-5 text-fg-3">{i + 1}.</span>
                <span className="font-medium">{t}</span>
              </li>
            ))}
          </ol>
        </div>

        {/* Browser */}
        <div data-browser className="min-w-0 overflow-hidden rounded-[14px] border border-line bg-surface-1">
          <div className="flex items-center gap-2 border-b border-line px-3 py-2">
            <Monitor className="size-3.5 text-fg-2" />
            <span className="text-[12px] text-fg-2">Browser</span>
            <div className="ml-2 flex min-w-0 flex-1 items-center gap-1.5 rounded-full bg-canvas px-2.5 py-1">
              <Lock className="size-3 shrink-0 text-fg-3" />
              <span data-url className="truncate font-mono text-[11px] text-fg-2">https://news.ycombinator.com/</span>
            </div>
          </div>
          <div className="relative aspect-[16/10] bg-canvas">
            <div className="absolute inset-0 flex items-center justify-center text-[12px] text-fg-3">Waiting for the agent…</div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              data-frame
              src="/demo/hn-frame.jpg"
              alt="Screenshot the agent took of the Hacker News front page"
              className="absolute inset-0 size-full object-cover object-top"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
