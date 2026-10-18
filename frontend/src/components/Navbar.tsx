"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchModelStatus } from "@/lib/api";
import { 
  GitPullRequest, 
  Compass, 
  Terminal, 
  LayoutDashboard, 
  Cpu, 
  ShieldCheck, 
  Sparkles,
  Layers,
  BookOpen
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const [modelStatus, setModelStatus] = useState<any>(null);

  useEffect(() => {
    fetchModelStatus().then((res) => {
      if (res) setModelStatus(res);
    });
    const interval = setInterval(() => {
      fetchModelStatus().then((res) => {
        if (res) setModelStatus(res);
      });
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/explore", label: "Explore Repos", icon: Compass },
    { href: "/learn", label: "Beginner Guide", icon: BookOpen },
    { href: "/mentor", label: "AI Mentor", icon: Sparkles },
    { href: "/contributions", label: "Flight Recorder", icon: GitPullRequest },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 group-hover:border-emerald-400 transition-colors">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <span className="font-bold tracking-tight text-zinc-100 flex items-center gap-1.5 text-base">
                FirstPatch <span className="text-emerald-400 font-mono text-xs px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">AI</span>
              </span>
              <span className="text-[10px] text-zinc-400 block -mt-0.5">Open-Source Mentor</span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Status / Controls */}
        <div className="flex items-center gap-3">
          {/* Ollama Model Health Pill */}
          <Link
            href="/settings/models"
            className="flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/90 px-3 py-1 text-xs text-zinc-300 hover:border-zinc-700 transition-colors"
            title="Configure Local Model"
          >
            <span className="relative flex h-2 w-2">
              {modelStatus?.online ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </>
              ) : (
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
              )}
            </span>
            <span className="font-mono text-[11px] text-zinc-400 hidden sm:inline">
              {modelStatus?.online
                ? `${modelStatus.active_model || 'Local Ollama'}`
                : "Ollama: Offline"}
            </span>
            <Cpu className="h-3 w-3 text-zinc-400" />
          </Link>

          {/* Settings link */}
          <Link
            href="/settings/privacy"
            className="p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 border border-transparent hover:border-zinc-800 transition-colors"
            title="Privacy & Verification"
          >
            <ShieldCheck className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}
