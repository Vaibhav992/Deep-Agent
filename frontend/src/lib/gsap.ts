"use client";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { TextPlugin } from "gsap/TextPlugin";
import { useGSAP } from "@gsap/react";

// Register once, on the client. GSAP code itself only runs inside useGSAP (never during SSR).
gsap.registerPlugin(useGSAP, ScrollTrigger, SplitText, TextPlugin);

export const EASE_OUT = "power3.out";
export const EASE_IN_OUT = "power3.inOut";
export const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";
export const FULL_MOTION = "(prefers-reduced-motion: no-preference)";

export { gsap, useGSAP, ScrollTrigger, SplitText };
