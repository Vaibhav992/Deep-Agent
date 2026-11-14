import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Instrument_Sans, Spline_Sans_Mono } from "next/font/google";
import { APP_NAME } from "@/lib/brand";
import { THEME_BOOT_SCRIPT } from "@/lib/theme-script";
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
        variables: {
          colorPrimary: "#17171c",
          colorPrimaryForeground: "#ffffff",
          colorBackground: "#ffffff",
          colorInput: "#ffffff",
          colorInputForeground: "#17171c",
          colorForeground: "#17171c",
          colorMutedForeground: "#55555e",
          colorBorder: "rgb(23 23 28 / 0.14)",
          colorDanger: "#c4372b",
          borderRadius: "10px",
        },
      }}
    >
      {/* data-theme is set by the boot script before hydration, so the attribute may differ from the server. */}
      <html lang="en" className={`${body.variable} ${type.variable} h-full`} suppressHydrationWarning>
        <head>
          <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
        </head>
        <body className="h-full">{children}</body>
      </html>
    </ClerkProvider>
  );
}
