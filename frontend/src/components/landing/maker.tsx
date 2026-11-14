/* eslint-disable @next/next/no-img-element */
import { ArrowUpRight } from "lucide-react";
import { APP_NAME } from "@/lib/brand";

export const MAKER = {
  name: "Vaibhav Sharma",
  role: "AI engineer",
  photo: "/team/vaibhav-sharma.png",
  linkedin: "https://www.linkedin.com/in/vaibhav-sharma-6401b4214/",
};

// In my own words: the principles I gave myself while building this. Edit freely.
const BELIEFS = [
  {
    title: "Show the work.",
    body: "If I can't see what an agent did, I can't trust what it says. Every step should be visible while it happens, not summarised afterwards.",
  },
  {
    title: "No fake activity. Ever.",
    body: "What you see should be what actually happened: real pages, real screenshots, real failures. A good-looking demo isn't a product.",
  },
  {
    title: "Failures should be loud.",
    body: "When something breaks, the agent should say so plainly. A confident answer that hides a failure is worse than no answer.",
  },
  {
    title: "Working beats existing.",
    body: "A feature isn't done because the code exists. It's done when it works, tested against the real thing, not against my assumptions.",
  },
];

export function LinkedInIcon({ className = "size-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true">
      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.07 2.07 0 1 1 0-4.13 2.07 2.07 0 0 1 0 4.13ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0Z" />
    </svg>
  );
}

/** Photo in a soft ring; the source image is already a circle crop, so a slight zoom hides its edge. */
export function MakerAvatar({ size = 120, ring = true }: { size?: number; ring?: boolean }) {
  return (
    <span
      className={`relative inline-block shrink-0 overflow-hidden rounded-full ${
        ring ? "shadow-[0_0_0_4px_var(--canvas),0_0_0_5px_var(--line),0_10px_24px_rgb(0_0_0/0.12)]" : ""
      }`}
      style={{ width: size, height: size }}
    >
      <img src={MAKER.photo} alt={`${MAKER.name}, developer of ${APP_NAME}`} className="size-full scale-[1.06] object-cover" />
    </span>
  );
}

export default function MakerSection() {
  return (
    <section className="mx-auto max-w-[1280px] px-6 py-24 sm:py-32" aria-labelledby="maker-title">
      <div className="mx-auto max-w-[760px] text-center">
        <p className="eyebrow text-fg-3">From the developer</p>
        <h2 id="maker-title" className="font-display mt-6 text-[34px] leading-[40px] text-balance sm:text-[48px] sm:leading-[54px]">
          An agent you can&apos;t watch is an agent you can&apos;t trust.
        </h2>
        <p className="mx-auto mt-7 max-w-[600px] text-[17px] leading-[28px] text-pretty text-fg-2">
          I build AI agents, and I care about one thing above the rest: that you can see what they&apos;re doing. {APP_NAME}{" "}
          plans, opens real pages and shows every step as it happens. The agent graph, the browser runtime, the guardrails,
          the memory and this interface are all built around that one idea.
        </p>
      </div>

      <div className="mx-auto mt-16 max-w-[1080px]">
        <p className="eyebrow text-center text-fg-3">How I think about agents</p>
        <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {BELIEFS.map((b, i) => (
            <li key={b.title} className="rounded-[18px] bg-cream p-6 text-left">
              <span className="font-mono text-[12px] text-fg-3">0{i + 1}</span>
              <h3 className="mt-4 text-[17px] font-medium leading-6 tracking-[-0.01em]">{b.title}</h3>
              <p className="mt-2 text-[14px] leading-[22px] text-pretty text-fg-2">{b.body}</p>
            </li>
          ))}
        </ul>
      </div>

      {/* The work leads; the signature follows. */}
      <div className="mx-auto mt-14 flex max-w-[1080px] flex-col items-center justify-center gap-4 sm:flex-row sm:gap-5">
        <div className="flex items-center gap-3">
          <MakerAvatar size={48} />
          <div className="text-left">
            <p className="text-[15px] font-medium leading-5">{MAKER.name}</p>
            <p className="eyebrow mt-1 text-fg-3">{MAKER.role} · developer of {APP_NAME}</p>
          </div>
        </div>
        <a href={MAKER.linkedin} target="_blank" rel="noopener noreferrer" className="btn-ghost press px-4 py-2 text-[13px]">
          <LinkedInIcon className="size-3.5 text-[#0A66C2]" />
          LinkedIn
          <ArrowUpRight className="size-3.5 text-fg-3" />
        </a>
      </div>
    </section>
  );
}
