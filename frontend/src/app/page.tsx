"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { analyzeRepository } from "@/lib/api";
import { 
  ArrowRight, 
  Search, 
  ShieldCheck, 
  Cpu, 
  Terminal, 
  CheckCircle2, 
  Sparkles, 
  Layers, 
  FileCode2, 
  GitPullRequest, 
  Stethoscope,
  Compass,
  Key,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Zap
} from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Optional Gemma 4 API Key
  const [gemmaApiKey, setGemmaApiKey] = useState("");
  const [showKeyDrawer, setShowKeyDrawer] = useState(false);
  const [isKeySaved, setIsKeySaved] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("firstpatch_gemma_api_key") || localStorage.getItem("firstpatch_api_key");
      if (stored) {
        setGemmaApiKey(stored);
        setIsKeySaved(true);
      }
    }
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setLoading(true);
    setError(null);

    // Save key if entered
    if (gemmaApiKey.trim() && typeof window !== "undefined") {
      localStorage.setItem("firstpatch_gemma_api_key", gemmaApiKey.trim());
      localStorage.setItem("firstpatch_api_key", gemmaApiKey.trim());
      setIsKeySaved(true);
    }

    try {
      const res = await analyzeRepository(repoUrl.trim(), {
        apiKey: gemmaApiKey.trim() || undefined
      });
      router.push(`/repo/${res.owner}/${res.name}`);
    } catch (err: any) {
      setError(err.message || "Failed to analyze repository. Check the URL and try again.");
      setLoading(false);
    }
  };

  const sampleRepos = [
    { label: "Flask", url: "https://github.com/pallets/flask" },
    { label: "Typer", url: "https://github.com/tiangolo/typer" },
    { label: "FastAPI", url: "https://github.com/fastapi/fastapi" },
  ];

  const features = [
    {
      title: "Repository Reality Checker",
      desc: "Deterministic AST & symbol mapping grounds every explanation in exact lines and functions—zero code hallucination.",
      icon: FileCode2,
      badge: "Grounded RAG"
    },
    {
      title: "Contextual Issue Matcher",
      desc: "Filters and ranks open GitHub issues with transparent fit scores, complexity estimates, and prerequisite detection.",
      icon: Compass,
      badge: "Skill-Aware"
    },
    {
      title: "Setup Failure Doctor",
      desc: "Diagnoses dependency errors, peer conflicts, and environment bugs with safe, actionable remediation commands.",
      icon: Stethoscope,
      badge: "Build Diagnostics"
    },
    {
      title: "Dual-Mode Mentorship",
      desc: "Learn Mode teaches architecture with Socratic drills, while Copilot Mode provides scoped patches and test targets.",
      icon: Sparkles,
      badge: "Socratic AI"
    },
    {
      title: "Contribution Flight Recorder",
      desc: "Logs every step from Understand to Verify, capturing raw test outputs into a maintainer-ready PR checklist.",
      icon: GitPullRequest,
      badge: "Truthful PRs"
    },
  ];

  return (
    <div className="relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-emerald-500/10 via-cyan-500/5 to-transparent blur-3xl pointer-events-none -z-10" />

      {/* Hero Section */}
      <section className="pt-20 pb-16 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-medium mb-6">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Local-First AI Open-Source Contribution Mentor</span>
        </div>

        {/* Heading */}
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-zinc-100 max-w-4xl mx-auto leading-tight">
          Don&apos;t just generate code.{" "}
          <span className="bg-gradient-to-r from-emerald-400 via-cyan-400 to-teal-300 bg-clip-text text-transparent">
            Understand, contribute, and verify.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="mt-6 text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          FirstPatch AI connects to any public GitHub repository, parses its AST to map real functions and tests, diagnoses environment setup errors, and guides you to a maintainer-ready pull request.
        </p>

        {/* Input Form */}
        <form onSubmit={handleAnalyze} className="mt-10 max-w-2xl mx-auto">
          <div className="relative flex items-center shadow-2xl rounded-xl border border-zinc-700 bg-zinc-900/90 p-1.5 focus-within:border-emerald-500 transition-colors">
            <Search className="h-5 w-5 text-zinc-400 ml-3 shrink-0" />
            <input
              type="text"
              placeholder="Paste GitHub URL (e.g. https://github.com/pallets/flask or owner/repo)"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              className="w-full bg-transparent px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !repoUrl.trim()}
              className="flex items-center gap-2 rounded-lg bg-emerald-500 px-5 py-2.5 text-xs font-semibold text-zinc-950 hover:bg-emerald-400 disabled:opacity-50 transition-all shrink-0 cursor-pointer"
            >
              {loading ? (
                <>
                  <span className="h-3.5 w-3.5 border-2 border-zinc-950 border-t-transparent rounded-full animate-spin"></span>
                  Analyzing...
                </>
              ) : (
                <>
                  Analyze Repository
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400 text-left">
              {error}
            </div>
          )}

          {/* Quick Repo Suggestions */}
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs text-zinc-400">
            <span>Try an open-source project:</span>
            {sampleRepos.map((s) => (
              <button
                key={s.url}
                type="button"
                onClick={() => setRepoUrl(s.url)}
                className="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:border-zinc-700 hover:text-emerald-400 transition-colors cursor-pointer"
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* Gemma 4 Optional API Key Drawer */}
          <div className="mt-4 pt-2 flex flex-col items-center">
            <button
              type="button"
              onClick={() => setShowKeyDrawer(!showKeyDrawer)}
              className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-indigo-400 transition-colors cursor-pointer"
            >
              <Key className="h-3 w-3 text-indigo-400" />
              <span>
                {isKeySaved
                  ? "✨ Gemma 4 Cloud Key Active (click to edit)"
                  : "+ Add Gemma 4 API Key for Deep Analysis"}
              </span>
              {showKeyDrawer ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>

            {showKeyDrawer && (
              <div className="mt-3 w-full max-w-lg p-3.5 rounded-xl border border-indigo-500/30 bg-zinc-950/90 text-left space-y-2 shadow-xl">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-zinc-200 flex items-center gap-1.5">
                    <Zap className="h-3.5 w-3.5 text-indigo-400" />
                    Gemma 4 Deep Repository Intelligence
                  </span>
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5"
                  >
                    <span>Get Free Key</span>
                    <ExternalLink className="h-2.5 w-2.5" />
                  </a>
                </div>
                <p className="text-[11px] text-zinc-400">
                  Provide a Google AI Studio or OpenRouter API key to automatically extract architectural patterns, beginner safe zones, and contribution quickstarts.
                </p>
                <div className="flex gap-2">
                  <input
                    type="password"
                    placeholder="AIzaSy... or OpenRouter sk-or-..."
                    value={gemmaApiKey}
                    onChange={(e) => setGemmaApiKey(e.target.value)}
                    className="flex-1 px-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900 text-xs font-mono text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500"
                  />
                  {gemmaApiKey && (
                    <button
                      type="button"
                      onClick={() => {
                        setGemmaApiKey("");
                        if (typeof window !== "undefined") {
                          localStorage.removeItem("firstpatch_gemma_api_key");
                          localStorage.removeItem("firstpatch_api_key");
                        }
                        setIsKeySaved(false);
                      }}
                      className="px-2 py-1 text-[11px] text-zinc-500 hover:text-red-400 cursor-pointer"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </form>

        {/* Local Privacy Callout */}
        <div className="mt-12 inline-flex items-center gap-6 text-xs text-zinc-400 border-t border-zinc-900 pt-6">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-emerald-400" />
            <span>Runs locally with Gemma / Qwen via Ollama</span>
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-cyan-400" />
            <span>Zero telemetry or code leakage</span>
          </div>
        </div>
      </section>

      {/* 5-Stage Pipeline Overview */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-t border-zinc-900">
        <div className="text-center mb-12">
          <h2 className="text-xs uppercase tracking-widest font-mono text-emerald-400 mb-2">The Complete Contribution Pipeline</h2>
          <p className="text-2xl sm:text-3xl font-bold text-zinc-100">From repository confusion to a verified pull request</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <div 
                key={f.title}
                className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-5 hover:border-zinc-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="h-9 w-9 rounded-lg bg-zinc-800 flex items-center justify-center text-emerald-400 border border-zinc-700/50">
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="font-mono text-[10px] text-zinc-400">0{i + 1}</span>
                  </div>
                  <div className="inline-block px-2 py-0.5 rounded bg-zinc-800/80 text-[10px] font-mono text-zinc-400 mb-2 border border-zinc-700/40">
                    {f.badge}
                  </div>
                  <h3 className="text-sm font-semibold text-zinc-200 mb-2">{f.title}</h3>
                  <p className="text-xs text-zinc-400 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* CTA Box */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
        <div className="rounded-2xl border border-zinc-800 bg-gradient-to-r from-zinc-900 via-zinc-900/90 to-zinc-950 p-8 sm:p-10 text-center relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
          <h3 className="text-2xl font-bold text-zinc-100 mb-3">Ready to make your first verified contribution?</h3>
          <p className="text-sm text-zinc-400 max-w-xl mx-auto mb-6">
            Explore active open-source repositories or connect your target project to begin your guided mentorship journey.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/explore"
              className="px-5 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer"
            >
              Explore Repositories
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <Link
              href="/dashboard"
              className="px-5 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800/60 hover:bg-zinc-800 text-zinc-200 text-xs font-semibold transition-all cursor-pointer"
            >
              View Dashboard
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
