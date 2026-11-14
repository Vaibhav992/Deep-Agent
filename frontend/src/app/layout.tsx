import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: "Deep Agent",
  description: "An agent that researches the web and works in a real browser, and shows you every step.",
};

export const viewport: Viewport = {
  themeColor: "#08090a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider
      appearance={{
        theme: dark,
        variables: {
          colorPrimary: "#c6f432",
          colorPrimaryForeground: "#0b0f02",
          colorBackground: "#0e1011",
          colorInput: "#141719",
          colorInputForeground: "#eceeea",
          colorForeground: "#eceeea",
          colorMutedForeground: "#a2a8a3",
          colorBorder: "rgb(255 255 255 / 0.12)",
          colorDanger: "#ff6b5b",
          borderRadius: "8px",
        },
      }}
    >
      <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
        <body className="h-full">{children}</body>
      </html>
    </ClerkProvider>
  );
}
