"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  analyzeRepository,
  listRepositories,
  fetchHealth,
} from "@/lib/api";
import {
  Search,
  Sparkles,
  ArrowRight,
  Star,
  FileCode,
  Layers,
  CheckCircle2,
  AlertCircle,
  Cpu,
} from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [recentRepos, setRecentRepos] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listRepositories().then((res) => {
      if (Array.isArray(res)) setRecentRepos(res);
    });
    fetchHealth().then(setHealth);
  }, []);

  function validateURL(value: string): string {
    const val = value.trim();
    if (!val) return "Please enter a GitHub repository URL or owner/repo";
    if (val.includes("github.com")) {
      const parts = val.replace(/^https?:\/\//i, "").replace(/^github\.com\//i, "").split("/");
      if (parts.length < 2 || !parts[0] || !parts[1]) return "URL must include owner and repository name";
    } else {
      const parts = val.split("/");
      if (parts.length !== 2 || !parts[0] || !parts[1]) return "Format must be owner/repo (e.g. tiangolo/fastapi)";
    }
    return "";
  }

  async function handleSubmit(e: React.FormEvent, customUrl?: string) {
    if (e) e.preventDefault();
    const targetUrl = customUrl || url;
    const validationError = validateURL(targetUrl);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await analyzeRepository(targetUrl.trim());
      const owner = res.owner || res.repository?.identity?.owner;
      const repo = res.name || res.repository?.identity?.repo;
      if (owner && repo) {
        router.push(`/repo/${owner}/${repo}`);
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Failed to analyze repository. Ensure the backend is reachable.");
    } finally {
      setLoading(false);
    }
  }

  const demoRepos = [
    { label: "tiangolo/fastapi", url: "https://github.com/tiangolo/fastapi" },
    { label: "pallets/flask",    url: "https://github.com/pallets/flask" },
    { label: "encode/httpx",     url: "https://github.com/encode/httpx" },
    { label: "psf/requests",     url: "https://github.com/psf/requests" },
  ];

  return (
    <main className="flex-1 px-4 sm:px-6 py-12 max-w-7xl mx-auto w-full space-y-16">
      {/* ── Hero ── */}
      <div className="text-center max-w-4xl mx-auto animate-in">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white border border-brand-200/80 text-brand-700 text-xs font-bold mb-6 shadow-[0_2px_12px_rgba(124,58,237,0.09)]">
          <Sparkles className="w-3.5 h-3.5 text-brand-500" />
          Evidence-Backed Open-Source Mentor
          {health?.ai_provider && (
            <span className="ml-1 pl-2 border-l border-brand-200 font-mono text-[10px] text-gray-500 flex items-center gap-1">
              <Cpu className="w-3 h-3 text-brand-500" /> {health.ai_provider}
            </span>
          )}
        </div>
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight mb-5 text-gray-900 leading-[1.1]">
          Make your <span className="text-gradient glow-brand">first patch</span>
          <br />with confidence
        </h1>
        <p className="text-base sm:text-lg text-gray-600 leading-relaxed max-w-2xl mx-auto">
          Enter any public GitHub repository. FirstPatch AI inspects its structure with AST parsers, discovers
          beginner-friendly issues, and crafts an evidence-backed contribution roadmap.
        </p>
      </div>

      {/* ── Repository Input Card ── */}
      <div className="max-w-2xl mx-auto animate-up">
        <form onSubmit={(e) => handleSubmit(e)} noValidate>
          <div className="card-brand">
            <label htmlFor="repo-url" className="section-label block mb-2.5 text-brand-700">
              Analyze GitHub Repository
            </label>
            <div className="flex gap-3 flex-col sm:flex-row">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  id="repo-url"
                  ref={inputRef}
                  type="text"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    if (error) setError(validateURL(e.target.value));
                  }}
                  placeholder="https://github.com/owner/repo or owner/repo"
                  className={`input pl-11 ${error ? "border-rose-400 ring-2 ring-rose-200" : ""}`}
                  disabled={loading}
                  autoComplete="off"
                  autoFocus
                />
              </div>
              <button
                id="btn-analyze"
                type="submit"
                disabled={loading || !url.trim()}
                className="btn-primary shrink-0 justify-center py-3 px-6 shadow-md"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    Analyzing Codebase…
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Search className="w-4 h-4" />
                    Analyze Repository
                  </span>
                )}
              </button>
            </div>
            {error && (
              <p id="url-error" className="mt-3 text-xs text-rose-600 flex items-center gap-1.5 font-medium" role="alert">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                {error}
              </p>
            )}
          </div>

          <div className="mt-4 text-center">
            <p className="text-xs text-gray-500 font-medium mb-2">📌 Try a verified public repository:</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {demoRepos.map((r) => (
                <button
                  key={r.url}
                  type="button"
                  onClick={() => {
                    setUrl(r.url);
                    setError("");
                    inputRef.current?.focus();
                  }}
                  className="btn-secondary text-xs py-1.5 px-3.5 rounded-full hover:border-brand-300"
                  id={`demo-${r.label.replace("/", "-")}`}
                >
                  <FileCode className="w-3.5 h-3.5 text-brand-500" />
                  {r.label}
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>

      {/* ── Recently Indexed Repositories ── */}
      {recentRepos.length > 0 && (
        <div className="space-y-4 animate-up">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Indexed Repositories</h2>
              <p className="text-xs text-gray-500">Repositories ready for immediate exploration and issue investigation</p>
            </div>
            <Link href="/dashboard" className="text-xs font-bold text-brand-600 hover:text-brand-800 flex items-center gap-1">
              View all in Dashboard <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentRepos.slice(0, 6).map((repo) => (
              <Link
                key={repo.id}
                href={`/repo/${repo.owner}/${repo.name}`}
                className="card-hover p-5 flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="badge-brand font-mono text-[10px]">{repo.language || "Codebase"}</span>
                    {repo.stars > 0 && (
                      <span className="flex items-center gap-1 text-xs text-amber-600 font-bold">
                        <Star className="w-3 h-3 fill-amber-400" /> {repo.stars.toLocaleString()}
                      </span>
                    )}
                  </div>
                  <h3 className="text-base font-bold text-gray-900 group-hover:text-brand-700 transition-colors">
                    {repo.id}
                  </h3>
                  {repo.description && (
                    <p className="text-xs text-gray-500 line-clamp-2 mt-1.5 leading-relaxed">
                      {repo.description}
                    </p>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs font-semibold text-brand-600">
                  <span>Explore Architecture &amp; Issues</span>
                  <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── 5 Bento Feature Cards ── */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Built for Open-Source Onboarding</h2>
          <p className="text-xs text-gray-500">Evidence-grounded toolchain from discovery to maintainer pull request</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 animate-up">
          {/* Card 1 — Repository Intelligence */}
          <Link href="/explore" className="card-hover p-6 flex flex-col justify-between group">
            <div>
              <div className="visual-panel min-h-[190px] mb-5">
                <div className="w-full flex flex-col gap-2">
                  <div className="floating-pill">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-brand-100 flex items-center justify-center text-brand-600">
                        <FileCode className="w-3.5 h-3.5" />
                      </span>
                      <span>Codebase Mapping</span>
                    </div>
                    <span className="text-gray-400 font-bold">98%</span>
                  </div>
                  <div className="floating-pill">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-purple-100 flex items-center justify-center text-purple-600">
                        <Layers className="w-3.5 h-3.5" />
                      </span>
                      <span>Framework Detection</span>
                    </div>
                    <span className="text-gray-400 font-bold">82%</span>
                  </div>
                  <div className="floating-pill-active mt-1">
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center text-white text-[10px] font-bold">
                        FP
                      </div>
                      <span>AST Symbol Indexing</span>
                    </div>
                    <span className="font-mono text-purple-200">READY</span>
                  </div>
                </div>
              </div>
              <h3 className="text-base font-bold text-gray-900 group-hover:text-brand-700 transition-colors mb-1.5">
                Repository Intelligence
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                AST symbol tables index functions, classes, imports, and test suites across the repository for instant grounded exploration.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between text-xs font-bold text-brand-600">
              <span>Explore Codebases</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>

          {/* Card 2 — 5-Factor Issue Matching */}
          <Link href="/explore" className="card-hover p-6 flex flex-col justify-between group">
            <div>
              <div className="visual-panel-purple min-h-[190px] mb-5">
                <div className="relative flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-brand-600 to-purple-600 text-white flex items-center justify-center font-extrabold text-sm shadow-xl z-10">
                    AI
                  </div>
                  <div className="absolute -left-12 w-8 h-8 rounded-full bg-white shadow-sm flex items-center justify-center text-xs font-bold text-brand-600">
                    FIT
                  </div>
                  <div className="absolute -right-12 w-8 h-8 rounded-full bg-white shadow-sm flex items-center justify-center text-xs font-bold text-purple-600">
                    AST
                  </div>
                </div>
                <div className="mt-4 px-3 py-1 rounded-full bg-white/90 border border-purple-200 text-[10px] font-bold text-purple-900 shadow-sm">
                  5-Factor Multi-Dimensional Fit
                </div>
              </div>
              <h3 className="text-base font-bold text-gray-900 group-hover:text-brand-700 transition-colors mb-1.5">
                Intelligent Issue Matching
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                Evaluates Technical Fit, Evidence Confidence, Contribution Viability, and Learning Value to pair beginners with achievable issues.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between text-xs font-bold text-brand-600">
              <span>Find Suitable Issues</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>

          {/* Card 3 — Setup Failure Doctor */}
          <Link href="/learn" className="card-hover p-6 flex flex-col justify-between group">
            <div>
              <div className="visual-panel min-h-[190px] mb-5">
                <div className="w-full flex flex-col gap-2 z-10">
                  <div className="bg-white/95 rounded-2xl p-3 text-[11px] text-gray-800 shadow-sm border border-white">
                    <span className="text-rose-600 font-bold block mb-0.5">Setup Diagnostic</span>
                    <code className="text-[10px] font-mono text-gray-600">ModuleNotFoundError: pytest</code>
                  </div>
                  <div className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-2xl p-2.5 text-[11px] shadow-sm flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-200" />
                    <span className="truncate">Safe fix: <code className="bg-white/20 px-1 rounded text-[10px]">pip install -r requirements.txt</code></span>
                  </div>
                </div>
              </div>
              <h3 className="text-base font-bold text-gray-900 group-hover:text-brand-700 transition-colors mb-1.5">
                Setup Failure Doctor
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                Deterministic regex signatures diagnose onboarding errors, missing dependencies, and configuration gotchas with safe remediation commands.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between text-xs font-bold text-brand-600">
              <span>Read Diagnostic Guide</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>

          {/* Card 4 — Contributor Triage Gate */}
          <Link href="/learn" className="card-hover p-6 flex flex-col justify-between group">
            <div>
              <div className="visual-panel-purple min-h-[190px] mb-5">
                <div className="w-full space-y-2">
                  <div className="floating-pill">
                    <span>1. Restate Problem</span>
                    <span className="text-emerald-600 font-bold">✓</span>
                  </div>
                  <div className="floating-pill">
                    <span>2. Minimal Reproduction</span>
                    <span className="text-emerald-600 font-bold">✓</span>
                  </div>
                  <div className="floating-pill">
                    <span>3. Hypothesis Log</span>
                    <span className="text-emerald-600 font-bold">✓</span>
                  </div>
                  <div className="floating-pill-active">
                    <span>Decision Gate</span>
                    <span className="text-purple-300 font-mono">PROCEED</span>
                  </div>
                </div>
              </div>
              <h3 className="text-base font-bold text-gray-900 group-hover:text-brand-700 transition-colors mb-1.5">
                Triage Before Codegen
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                Guides new contributors through structured problem formulation to prevent low-effort AI pull request spam on open-source maintainers.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between text-xs font-bold text-brand-600">
              <span>View Triage Lifecycle</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>

          {/* Card 5 — Flight Recorder & Verification (Span 2) */}
          <Link href="/contributions" className="card-hover p-6 md:col-span-1 lg:col-span-2 flex flex-col justify-between group">
            <div>
              <div className="visual-panel min-h-[190px] mb-5 w-full">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 w-full max-w-lg bg-white/90 backdrop-blur-md rounded-2xl px-5 py-4 border border-white shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-brand-500 text-white flex items-center justify-center font-bold text-xs">
                      FR
                    </div>
                    <div>
                      <p className="text-xs font-bold text-gray-800">Flight Recorder Event Ledger</p>
                      <p className="text-[10px] text-gray-500">Auditable verification steps, diff checks, and test logs</p>
                    </div>
                  </div>
                  <span className="badge-success text-xs font-bold px-3 py-1">
                    100% Grounded
                  </span>
                </div>
              </div>
              <h3 className="text-base font-bold text-gray-900 group-hover:text-brand-700 transition-colors mb-1.5">
                Flight Recorder &amp; Review Simulation
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                Executes automated tests in isolated environments, simulates code review before pull request submission, and produces a complete audit trail.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between text-xs font-bold text-brand-600">
              <span>Open Flight Recorder Workspaces</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>
        </div>
      </div>
    </main>
  );
}
