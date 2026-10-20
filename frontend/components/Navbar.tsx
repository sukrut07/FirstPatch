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
  Search,
  Menu,
  X,
  Settings,
  ChevronRight,
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    fetchModelStatus().then((res) => { if (res) setModelStatus(res); });
    fetchHealth().then((res) => { if (res) setHealth(res); });

    const interval = setInterval(() => {
      fetchModelStatus().then((res) => { if (res) setModelStatus(res); });
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Close sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  const navLinks = [
    { href: "/dashboard",     label: "Dashboard",       icon: LayoutDashboard, id: "nav-dashboard" },
    { href: "/explore",       label: "Explore Repos",   icon: Compass,         id: "nav-explore-repos" },
    { href: "/learn",         label: "Beginner Guide",  icon: BookOpen,        id: "nav-beginner-guide" },
    { href: "/mentor",        label: "AI Mentor",       icon: Sparkles,        id: "nav-ai-mentor" },
    { href: "/contributions", label: "Flight Recorder", icon: GitPullRequest,  id: "nav-flight-recorder" },
    { href: "/compliance",    label: "Trust Audit",     icon: ShieldCheck,     id: "nav-trust-audit" },
  ];

  const settingsLinks = [
    { href: "/settings",         label: "Settings Hub",     icon: Settings },
    { href: "/settings/models",  label: "AI Models",        icon: Cpu },
    { href: "/settings/privacy", label: "Privacy & Data",   icon: ShieldCheck },
  ];

  return (
    <>
      <header className="sticky top-0 z-40 glass border-b border-white/70 shadow-[0_2px_12px_rgba(124,58,237,0.06)]">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Brand & Sidebar Toggle */}
          <div className="flex items-center gap-3 sm:gap-6">
            <button
              id="nav-sidebar-toggle"
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-2xl text-gray-600 hover:text-brand-700 hover:bg-white/80 transition-colors focus:outline-none"
              title="Open Navigation Menu"
              aria-label="Open Navigation Menu"
            >
              <Menu className="h-5 w-5" />
            </button>

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

            {/* Desktop Navigation Links */}
            <nav className="hidden lg:flex items-center gap-1 ml-2">
              {navLinks.map((link) => {
                const Icon = link.icon;
                const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    id={link.id}
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
          <div className="flex items-center gap-2 sm:gap-3">
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

            {/* Settings Link */}
            <Link
              href="/settings"
              id="nav-settings-link"
              className="p-2 rounded-2xl text-gray-600 hover:text-brand-700 hover:bg-white/80 border border-transparent hover:border-brand-100 transition-colors shadow-none hover:shadow-sm"
              title="Settings Hub"
            >
              <Settings className="h-4 w-4" />
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

      {/* Responsive Navigation Sidebar Drawer */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm transition-opacity animate-in"
            onClick={() => setSidebarOpen(false)}
          />

          {/* Drawer Panel */}
          <aside
            id="sidebar-drawer"
            className="relative flex flex-col w-72 sm:w-80 max-w-[85vw] h-full bg-white shadow-2xl border-r border-gray-200/90 z-10 animate-up"
            style={{ animationDuration: "0.25s" }}
          >
            {/* Drawer Header */}
            <div className="flex items-center justify-between p-5 border-b border-gray-100">
              <Link href="/" onClick={() => setSidebarOpen(false)} className="flex items-center gap-2.5">
                <div
                  className="w-8 h-8 rounded-xl flex items-center justify-center text-white text-xs font-black shadow-md"
                  style={{ background: "linear-gradient(135deg, #6366f1 0%, #7c3aed 100%)" }}
                >
                  FP
                </div>
                <div>
                  <span className="font-extrabold text-gray-900 text-sm">FirstPatch AI</span>
                  <span className="text-[10px] text-gray-400 block font-medium">Contributor Navigation</span>
                </div>
              </Link>

              <button
                id="nav-sidebar-close"
                onClick={() => setSidebarOpen(false)}
                className="p-1.5 rounded-xl text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                aria-label="Close Navigation"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Navigation Links */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              <div>
                <p className="section-label px-3 mb-2 text-gray-400">Workspaces &amp; Discovery</p>
                <div className="space-y-1">
                  {navLinks.map((link) => {
                    const Icon = link.icon;
                    const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
                    return (
                      <Link
                        key={link.href}
                        href={link.href}
                        onClick={() => setSidebarOpen(false)}
                        id={`sidebar-${link.id}`}
                        className={`flex items-center justify-between px-3.5 py-2.5 rounded-2xl text-xs font-bold transition-all ${
                          isActive
                            ? "bg-brand-50 text-brand-700 border border-brand-200/80 shadow-sm"
                            : "text-gray-600 hover:bg-surface-50 hover:text-gray-900"
                        }`}
                      >
                        <span className="flex items-center gap-3">
                          <Icon className={`w-4 h-4 ${isActive ? "text-brand-600" : "text-gray-400"}`} />
                          {link.label}
                        </span>
                        {isActive && <span className="w-1.5 h-1.5 rounded-full bg-brand-600" />}
                      </Link>
                    );
                  })}
                </div>
              </div>

              <div>
                <p className="section-label px-3 mb-2 text-gray-400">System &amp; Settings</p>
                <div className="space-y-1">
                  {settingsLinks.map((link) => {
                    const Icon = link.icon;
                    const isActive = pathname === link.href;
                    return (
                      <Link
                        key={link.href}
                        href={link.href}
                        onClick={() => setSidebarOpen(false)}
                        className={`flex items-center justify-between px-3.5 py-2.5 rounded-2xl text-xs font-bold transition-all ${
                          isActive
                            ? "bg-brand-50 text-brand-700 border border-brand-200/80 shadow-sm"
                            : "text-gray-600 hover:bg-surface-50 hover:text-gray-900"
                        }`}
                      >
                        <span className="flex items-center gap-3">
                          <Icon className={`w-4 h-4 ${isActive ? "text-brand-600" : "text-gray-400"}`} />
                          {link.label}
                        </span>
                        <ChevronRight className="w-3.5 h-3.5 text-gray-300" />
                      </Link>
                    );
                  })}
                </div>
              </div>

              {/* Quick Analyze CTA */}
              <div className="p-4 rounded-2xl bg-surface-50 border border-gray-200/80 space-y-2">
                <div className="flex items-center gap-2 text-brand-700 font-bold text-xs">
                  <Search className="w-4 h-4" />
                  <span>Analyze Codebase</span>
                </div>
                <p className="text-[11px] text-gray-500 leading-relaxed">
                  Enter any public GitHub repository to extract AST symbol tables and discover issues.
                </p>
                <Link
                  href="/"
                  onClick={() => setSidebarOpen(false)}
                  className="btn-primary text-xs py-2 px-3.5 rounded-xl w-full justify-center font-bold"
                >
                  Analyze New Repo
                </Link>
              </div>
            </div>

            {/* Drawer Footer with Status */}
            <div className="p-4 border-t border-gray-100 bg-surface-50/60 text-xs">
              <div className="flex items-center justify-between font-mono text-[11px] text-gray-600">
                <span className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${modelStatus?.online ? "bg-emerald-500" : "bg-amber-500"}`} />
                  {modelStatus?.online ? "Ollama Active" : "Grounded Engine"}
                </span>
                <span className="text-gray-400">v0.1.0</span>
              </div>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
