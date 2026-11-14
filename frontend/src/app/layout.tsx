import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Instrument_Sans, Spline_Sans_Mono } from "next/font/google";
import { APP_NAME } from "@/lib/brand";
import { THEME_BOOT_SCRIPT } from "@/lib/theme-script";
import Toaster from "@/components/toaster";
import "./globals.css";

// Swiss grotesk for the UI and body; a typewriter mono for display type, labels and machine text.
const body = Instrument_Sans({ subsets: ["latin"], variable: "--font-body" });
const type = Spline_Sans_Mono({ subsets: ["latin"], variable: "--font-type" });

export const metadata: Metadata = {
  title: APP_NAME,
  description: "An agent that researches the web and works in a real browser, and shows you every step.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#111311" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider
      appearance={{
        // Clerk reads our CSS tokens directly, so its cards and menus follow the light/dark slider.
        // Hard-coded light hex values here left the user menu's action text white-on-white in dark mode.
        variables: {
          colorPrimary: "var(--ink)",
          colorPrimaryForeground: "var(--on-ink)",
          colorBackground: "var(--canvas)",
          colorNeutral: "var(--fg)",
          colorForeground: "var(--fg)",
          colorMutedForeground: "var(--fg-2)",
          colorMuted: "var(--surface-2)",
          colorInput: "var(--canvas)",
          colorInputForeground: "var(--fg)",
          colorBorder: "var(--line-strong)",
          colorRing: "var(--ink)",
          colorDanger: "var(--danger)",
          colorShadow: "rgb(0 0 0 / 0.12)",
          fontFamily: "var(--font-sans)",
          borderRadius: "10px",
        },
        elements: {
          userButtonPopoverCard: "border border-[var(--line)] shadow-[0_8px_30px_rgb(0_0_0/0.12)]",
          userButtonPopoverActionButton: "text-[var(--fg)] hover:bg-[var(--surface-2)]",
          userButtonPopoverActionButton__signOut: "hover:text-[var(--danger)]",
        },
      }}
    >
      {/* data-theme is set by the boot script before hydration, so the attribute may differ from the server. */}
      <html lang="en" className={`${body.variable} ${type.variable} h-full`} suppressHydrationWarning>
        <head>
          <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
        </head>
        <body className="h-full">
          {children}
          <Toaster />
        </body>
      </html>
    </ClerkProvider>
  );
}
