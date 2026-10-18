import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "FirstPatch AI — Open-Source Mentor",
  description: "Turn unfamiliar repositories into verified, review-ready open source contributions with evidence-backed local AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col antialiased selection:bg-emerald-500/20 selection:text-emerald-300">
        <Suspense fallback={<div className="h-16 border-b border-zinc-800 bg-zinc-950" />}>
          <Navbar />
        </Suspense>
        <main className="flex-1">
          {children}
        </main>
        <footer className="border-t border-zinc-900 bg-zinc-950/60 py-6 px-4 text-center text-xs text-zinc-400">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
            <p>FirstPatch AI — Local-First Open-Source Contribution Copilot</p>
            <div className="flex items-center gap-4 text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 inline-block"></span>
                Grounded AST & Reality Checked
              </span>
              <span>•</span>
              <span>Local Model Privacy</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
