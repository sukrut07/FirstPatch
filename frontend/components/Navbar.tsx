"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchModelStatus, fetchHealth } from "@/lib/api";
import {
  LayoutDashboard,
  Compass,
  BookOpen,
  Sparkles,
  GitPullRequest,
  ShieldCheck,
  Cpu,
  Layers,
  Search,
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetchModelStatus().then((res) => { if (res) setModelStatus(res); });
    fetchHealth().then((res) => { if (res) setHealth(res); });

    const interval = setInterval(() => {
      fetchModelStatus().then((res) => { if (res) setModelStatus(res); });
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { href: "/dashboard",     label: "Dashboard",       icon: LayoutDashboard },
    { href: "/explore",       label: "Explore Repos",   icon: Compass },
    { href: "/learn",         label: "Beginner Guide",  icon: BookOpen },
    { href: "/mentor",        label: "AI Mentor",       icon: Sparkles },
    { href: "/contributions", label: "Flight Recorder", icon: GitPullRequest },
    { href: "/compliance",    label: "Trust Audit",     icon: ShieldCheck },
  ];

  return (
    <header className="sticky top-0 z-50 glass border-b border-white/70 shadow-[0_2px_12px_rgba(124,58,237,0.06)]">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 group" id="nav-brand">
            <div
              className="w-9 h-9 rounded-2xl flex items-center justify-center text-white text-xs font-black shadow-md transition-transform group-hover:scale-105"
              style={{
                background: "linear-gradient(135deg, #6366f1 0%, #7c3aed 100%)",
                boxShadow: "0 4px 14px rgba(124,58,237,0.32)",
              }}
            >
              FP
            </div>
            <div>
              <span className="font-extrabold tracking-tight text-gray-900 flex items-center gap-1.5 text-base leading-none">
                FirstPatch <span className="text-brand-600 font-mono text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-brand-50 border border-brand-200/80">AI</span>
              </span>
              <span className="text-[10px] text-gray-500 font-medium block mt-0.5">Open-Source Mentor</span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  id={`nav-${link.label.toLowerCase().replace(/\s+/g, "-")}`}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-2xl text-xs font-semibold transition-all duration-200 ${
                    isActive
                      ? "bg-white text-brand-700 shadow-[0_2px_8px_rgba(0,0,0,0.07)] border border-brand-100/90"
                      : "text-gray-600 hover:text-brand-700 hover:bg-white/60"
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
          {/* Quick Home / Analyze Link */}
          <Link
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl text-xs font-semibold text-gray-600 hover:text-brand-700 hover:bg-white/60 border border-transparent hover:border-brand-100 transition-colors"
            title="Analyze Repository"
          >
            <Search className="h-3.5 w-3.5 text-brand-500" />
            <span className="hidden sm:inline">Analyze Repo</span>
          </Link>

          {/* AI Model Status Pill */}
          <Link
            href="/settings/models"
            id="nav-model-status"
            className="flex items-center gap-2 rounded-full border border-gray-200/80 bg-white/90 px-3.5 py-1.5 text-xs text-gray-700 shadow-sm hover:border-brand-300 hover:text-brand-700 transition-colors"
            title="Configure AI Models & Ollama"
          >
            <span className="relative flex h-2 w-2">
              {modelStatus?.online ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </>
              ) : health?.ai_provider_status === "available" ? (
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              ) : (
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
              )}
            </span>
            <span className="font-mono text-[11px] font-bold text-gray-600 hidden sm:inline">
              {modelStatus?.online
                ? `${modelStatus.active_model || "Local Ollama"}`
                : health?.ai_provider_status === "available"
                ? `AI: ${health.ai_provider}`
                : "AI: Grounded"}
            </span>
            <Cpu className="h-3.5 w-3.5 text-brand-500" />
          </Link>

          {/* Privacy & Settings */}
          <Link
            href="/settings/privacy"
            id="nav-privacy-settings"
            className="p-2 rounded-2xl text-gray-600 hover:text-brand-700 hover:bg-white/80 border border-transparent hover:border-brand-100 transition-colors shadow-none hover:shadow-sm"
            title="Privacy & Security Boundaries"
          >
            <ShieldCheck className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}
