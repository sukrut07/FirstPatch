"use client";

import React, { useState, useCallback, useRef } from "react";
import {
  api,
  APIError,
  type RepositoryOverview,
  type MatchedIssue,
  type ContributionPlan,
  type HealthResponse,
} from "@/lib/api";
import {
  IconGitHub,
  IconSearch,
  IconSpinner,
  IconWarning,
  IconInfo,
  IconFolder,
  IconStar,
  IconBranch,
  IconExternal,
  IconSparkle,
  IconCursor,
  IconCode,
  IconLayers,
  ScoreBar,
  DifficultyBadge,
  EvidenceBadge,
  StatusIndicator,
  Skeleton,
  EmptyState,
  ErrorState,
  ExternalLink,
  IssueLabel,
  StatChip,
} from "@/components/ui";

type View = "home" | "overview" | "issues" | "plan" | "settings";

/* ─────────────────────────────────────────────────────────────────────
   Nav
───────────────────────────────────────────────────────────────────── */
function Nav({ view, setView, hasRepo, health }: {
  view: View; setView: (v: View) => void; hasRepo: boolean; health: HealthResponse | null;
}) {
  const navItems: { key: View; label: string; disabled?: boolean }[] = [
    { key: "home",     label: "Analyze" },
    { key: "overview", label: "Overview",  disabled: !hasRepo },
    { key: "issues",   label: "Issues",    disabled: !hasRepo },
    { key: "plan",     label: "Plan",      disabled: !hasRepo },
    { key: "settings", label: "Settings" },
  ];
  return (
    <nav className="sticky top-0 z-40 glass border-b border-white/60">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between gap-4 h-16">
        <div className="flex items-center gap-6">
          <button onClick={() => setView("home")} className="flex items-center gap-2.5 shrink-0 group" id="nav-logo">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center text-white text-xs font-black transition-transform group-hover:scale-105"
              style={{ background: "linear-gradient(135deg, #6366f1 0%, #7c3aed 100%)", boxShadow: "0 4px 14px rgba(124,58,237,0.32)" }}
            >
              FP
            </div>
            <span className="text-sm font-bold text-gradient hidden sm:block tracking-tight">FirstPatch AI</span>
          </button>
          <div className="flex items-center gap-1">
            {navItems.map((item) => (
              <button key={item.key} id={`nav-${item.key}`} disabled={item.disabled} onClick={() => setView(item.key)}
                className={`px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition-all duration-200 ${
                  view === item.key
                    ? "bg-white text-brand-700 shadow-[0_2px_8px_rgba(0,0,0,0.07)] border border-brand-100/80"
                    : item.disabled
                    ? "text-gray-400 cursor-not-allowed"
                    : "text-gray-600 hover:text-brand-700 hover:bg-white/60"}`}>
                {item.label}
              </button>
            ))}
          </div>
        </div>
        {health && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-gray-200/80 shadow-[0_2px_8px_rgba(0,0,0,0.03)] text-xs font-semibold text-gray-600">
            <span className={`w-2 h-2 rounded-full ${
              health.ai_provider_status === "available"      ? "bg-emerald-500 animate-pulse-slow" :
              health.ai_provider_status === "degraded"       ? "bg-amber-500 animate-pulse" :
              health.ai_provider_status === "not_configured" ? "bg-gray-400" : "bg-rose-500"}`} />
            <span className="hidden sm:inline">
              {health.ai_provider_status === "not_configured" ? "AI: Off" :
               health.ai_provider_status === "available"      ? `AI: ${health.ai_provider}` : "AI: Unavailable"}
            </span>
          </div>
        )}
      </div>
    </nav>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   HomeView
───────────────────────────────────────────────────────────────────── */
function HomeView({ onAnalyze }: { onAnalyze: (url: string) => void }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function validateURL(value: string): string {
    if (!value.trim()) return "Please enter a GitHub repository URL";
    if (!value.includes("github.com")) return "Only GitHub repositories are supported";
    const parts = value.replace(/^https?:\/\//, "").replace(/^github\.com\//, "").split("/");
    if (parts.length < 2 || !parts[0] || !parts[1]) return "URL must include owner and repository name";
    return "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validateURL(url);
    if (validationError) { setError(validationError); return; }
    setError(""); setLoading(true);
    try { await onAnalyze(url); } finally { setLoading(false); }
  }

  const demoRepos = [
    { label: "facebook/react",   url: "https://github.com/facebook/react" },
    { label: "tiangolo/fastapi", url: "https://github.com/tiangolo/fastapi" },
    { label: "vercel/next.js",   url: "https://github.com/vercel/next.js" },
    { label: "microsoft/vscode", url: "https://github.com/microsoft/vscode" },
  ];

  return (
    <main className="flex-1 px-4 sm:px-6 py-12 max-w-6xl mx-auto w-full">

      {/* ── Hero ── */}
      <div className="text-center mb-10 animate-in">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white border border-brand-200/80 text-brand-700 text-xs font-bold mb-6 shadow-[0_2px_12px_rgba(124,58,237,0.09)]">
          <IconSparkle className="w-3.5 h-3.5 text-brand-500" />
          AI-Powered Open-Source Mentor
        </div>
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight mb-4 text-gray-900 leading-[1.1]">
          Make your <span className="text-gradient glow-brand">first patch</span>
          <br />with confidence
        </h1>
        <p className="text-base sm:text-lg text-gray-500 leading-relaxed max-w-2xl mx-auto">
          Enter any public GitHub repository. FirstPatch AI inspects its structure, discovers
          beginner-friendly issues, and crafts an evidence-backed contribution roadmap.
        </p>
      </div>

      {/* ── Repository Input ── */}
      <div className="max-w-2xl mx-auto mb-14 animate-up">
        <form onSubmit={handleSubmit} noValidate>
          <div className="card-brand">
            <label htmlFor="repo-url" className="section-label block mb-2.5 text-brand-700">
              GitHub Repository URL
            </label>
            <div className="flex gap-3 flex-col sm:flex-row">
              <div className="flex-1 relative">
                <IconGitHub className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  id="repo-url" ref={inputRef} type="url" value={url}
                  onChange={(e) => { setUrl(e.target.value); if (error) setError(validateURL(e.target.value)); }}
                  placeholder="https://github.com/owner/repository"
                  className={`input pl-11 ${error ? "border-rose-400 ring-2 ring-rose-200" : ""}`}
                  disabled={loading} autoComplete="off" autoFocus
                  aria-describedby={error ? "url-error" : undefined} aria-invalid={!!error} />
              </div>
              <button id="btn-analyze" type="submit" disabled={loading || !url.trim()} className="btn-primary shrink-0 justify-center">
                {loading ? <IconSpinner /> : <IconSearch />}
                {loading ? "Analyzing…" : "Analyze Repository"}
              </button>
            </div>
            {error && (
              <p id="url-error" className="mt-2.5 text-xs text-rose-600 flex items-center gap-1.5 font-medium" role="alert">
                <IconWarning className="w-3.5 h-3.5 shrink-0" />{error}
              </p>
            )}
          </div>
          <div className="mt-4 text-center">
            <p className="text-xs text-gray-500 font-medium mb-2">📌 Try a demo repository:</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {demoRepos.map((r) => (
                <button key={r.url} type="button" onClick={() => { setUrl(r.url); setError(""); }}
                  className="btn-secondary text-xs py-1.5 px-3.5 rounded-full" id={`demo-${r.label.replace("/", "-")}`}>
                  <IconGitHub className="w-3.5 h-3.5 text-gray-500" />{r.label}
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>

      {/* ── Bento Feature Grid (5 cards matching reference screenshot) ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 animate-up">

        {/* Card 1 — Repository Intelligence (top-left) */}
        <div className="card-hover p-5 flex flex-col justify-between">
          <div className="visual-panel min-h-[220px] mb-5">
            <div className="w-full flex flex-col gap-2">
              {/* Floating metric pills */}
              <div className="floating-pill">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-brand-100 flex items-center justify-center text-brand-600">
                    <IconCode className="w-3.5 h-3.5" />
                  </span>
                  <span>Codebase Mapping</span>
                </div>
                <span className="text-gray-400 font-bold">98%</span>
              </div>
              <div className="floating-pill">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-purple-100 flex items-center justify-center text-purple-600">
                    <IconLayers className="w-3.5 h-3.5" />
                  </span>
                  <span>Framework Detection</span>
                </div>
                <span className="text-gray-400 font-bold">82%</span>
              </div>
              <div className="floating-pill">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
                    <IconFolder className="w-3.5 h-3.5" />
                  </span>
                  <span>Test Suite Hierarchy</span>
                </div>
                <span className="text-gray-400 font-bold">75%</span>
              </div>
              <div className="floating-pill-active mt-1">
                <div className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center text-white text-[10px]">
                    FP
                  </div>
                  <span className="tracking-tight">Predictive Mapping</span>
                </div>
                <span className="font-mono text-purple-300">4.2570</span>
              </div>
            </div>
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-1.5">Repository Intelligence</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Deep codebase mapping analyzes languages, frameworks, config files, test locations, and generates a verified AST snapshot.
            </p>
          </div>
        </div>

        {/* Card 2 — Intelligent Issue Matching (top-middle) */}
        <div className="card-hover p-5 flex flex-col justify-between">
          <div className="visual-panel-purple min-h-[220px] mb-5">
            {/* Concentric rings */}
            <div className="absolute w-44 h-44 rounded-full border border-purple-400/20 animate-pulse-slow" />
            <div className="absolute w-32 h-32 rounded-full border border-purple-400/30" />
            <div className="absolute w-20 h-20 rounded-full border border-purple-500/35" />
            {/* Orbital badge icons */}
            <div className="absolute top-4 left-6 w-8 h-8 rounded-full bg-white shadow-md flex items-center justify-center text-gray-700">
              <IconGitHub className="w-4 h-4" />
            </div>
            <div className="absolute top-5 right-6 w-8 h-8 rounded-full bg-white shadow-md flex items-center justify-center text-purple-600 font-mono text-[10px] font-bold">
              TS
            </div>
            <div className="absolute bottom-5 left-6 w-8 h-8 rounded-full bg-white shadow-md flex items-center justify-center text-indigo-600">
              <IconBranch className="w-4 h-4" />
            </div>
            <div className="absolute bottom-4 right-7 w-8 h-8 rounded-full bg-white shadow-md flex items-center justify-center text-amber-500">
              <IconStar className="w-4 h-4" />
            </div>
            {/* Center AI dial */}
            <div className="ai-dial z-10 flex items-center justify-center text-white text-xs font-black tracking-wider">
              AI
            </div>
            {/* Tooltip badge */}
            <div className="absolute bottom-7 z-20 flex items-center gap-1.5 bg-white px-3 py-1 rounded-full shadow-lg border border-purple-100 text-[11px] font-bold text-gray-800">
              <IconCursor className="w-3 h-3 text-purple-600" />
              <span>Smart Issue Match</span>
            </div>
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-1.5">Intelligent Issue Matching</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Ranks issues by 7 explicit criteria — comment density, newcomer friendliness, recency, and complexity — pairing you with ideal tasks.
            </p>
          </div>
        </div>

        {/* Card 3 — Contribution Plans (top-right) */}
        <div className="card-hover p-5 flex flex-col justify-between">
          <div className="visual-panel min-h-[220px] mb-5">
            {/* Glossy sphere decoration */}
            <div className="glossy-sphere w-8 h-8 absolute top-3 left-4" />
            <div className="w-full flex flex-col gap-2.5 z-10">
              {/* Chat-style plan preview */}
              <div className="bg-white/90 backdrop-blur-md rounded-2xl rounded-tl-sm p-3 text-[11px] text-gray-700 shadow-sm border border-white/80 max-w-[92%] leading-relaxed">
                Found issue #142. Here is your evidence-backed 3-step PR roadmap:
              </div>
              <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl rounded-tr-sm p-2.5 text-[11px] shadow-md max-w-[88%] self-end flex items-center gap-2">
                <span className="leading-tight">Step 1: Check <code className="bg-white/20 px-1 rounded text-[10px]">app/main.py</code></span>
                <span className="w-5 h-5 rounded-full bg-white/30 flex items-center justify-center text-[10px] font-bold shrink-0">✓</span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <div className="glossy-sphere w-4 h-4 shrink-0" />
                <div className="flex-1 flex flex-col gap-1">
                  <div className="h-1.5 w-3/4 rounded-full bg-white/80" />
                  <div className="h-1.5 w-1/2 rounded-full bg-white/60" />
                </div>
              </div>
            </div>
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-1.5">Contribution Plans</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Step-by-step implementation guides citing real file paths, AST checks, explicit assumptions, and suggested test suites.
            </p>
          </div>
        </div>

        {/* Card 4 — Setup Failure Doctor (bottom-left) */}
        <div className="card-hover p-5 flex flex-col justify-between">
          <div className="visual-panel-purple min-h-[200px] mb-5">
            {/* Watermark background text */}
            <div className="absolute inset-0 flex items-center justify-center opacity-10 select-none pointer-events-none text-[10px] font-mono leading-tight tracking-widest text-center px-4">
              DIAGNOSTIC &bull; DEPENDENCIES &bull; AST PARSER &bull; RESOLVER &bull; VERIFY &bull; STACK
            </div>
            {/* Node graph */}
            <div className="relative flex items-center justify-center">
              <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-purple-700 to-indigo-600 text-white flex items-center justify-center font-bold text-xs shadow-lg z-10">
                AI
              </div>
              <div className="absolute -left-12 w-7 h-7 rounded-full bg-white shadow-sm flex items-center justify-center text-xs font-mono font-bold text-indigo-600">PY</div>
              <div className="absolute -right-12 w-7 h-7 rounded-full bg-white shadow-sm flex items-center justify-center text-xs font-mono font-bold text-purple-600">JS</div>
              <div className="absolute -top-10 w-7 h-7 rounded-full bg-white shadow-sm flex items-center justify-center text-xs font-mono font-bold text-sky-600">CI</div>
              <div className="absolute -bottom-10 w-7 h-7 rounded-full bg-white shadow-sm flex items-center justify-center text-xs font-mono font-bold text-emerald-600">OK</div>
            </div>
            <div className="mt-4 px-3 py-1 rounded-full bg-white/80 border border-purple-100 text-[10px] font-bold text-purple-800 shadow-sm">
              Zero Setup Failures
            </div>
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-1.5">Setup Failure Doctor</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Detects runtime mismatches, missing dependencies, and configuration gotchas before you write your first line of code.
            </p>
          </div>
        </div>

        {/* Card 5 — Contribution Readiness (bottom-right, wide 2-col span) */}
        <div className="card-hover p-5 md:col-span-1 lg:col-span-2 flex flex-col justify-between">
          <div
            onClick={() => inputRef.current?.focus()}
            className="visual-panel min-h-[200px] mb-5 w-full cursor-pointer group"
          >
            {/* Ambient glow streak */}
            <div className="absolute inset-x-0 h-10 bg-gradient-to-r from-transparent via-purple-300/25 to-transparent blur-md pointer-events-none" />
            {/* Pill widget */}
            <div className="repo-pill-widget group-hover:scale-[1.01]">
              <div className="flex items-center gap-3">
                <IconGitHub className="w-4 h-4 text-purple-600 shrink-0" />
                <span className="text-xs font-bold text-gray-700">AI Repository Inspector</span>
              </div>
              <div className="px-4 py-1.5 rounded-full text-white text-xs font-bold flex items-center gap-1.5 shadow-sm"
                style={{ background: "linear-gradient(135deg, #6366f1 0%, #7c3aed 100%)" }}>
                <span>Analyze Repo</span>
                <IconSparkle className="w-3 h-3" />
              </div>
            </div>
            {/* Telemetry dash indicators */}
            <div className="flex gap-2 mt-4 opacity-60">
              <div className="w-12 h-1.5 rounded-full bg-white/80" />
              <div className="w-16 h-1.5 rounded-full bg-white/60" />
              <div className="w-10 h-1.5 rounded-full bg-white/80" />
              <div className="w-20 h-1.5 rounded-full bg-white/60" />
              <div className="w-12 h-1.5 rounded-full bg-white/80" />
            </div>
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-1.5">Contribution Readiness</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Our AI mentors map existing test suites, suggest targeted verification commands, and score your contribution readiness before you open your pull request.
            </p>
          </div>
        </div>

      </div>
    </main>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   OverviewView
───────────────────────────────────────────────────────────────────── */
function OverviewView({ repo, loading, error, onGoIssues }: {
  repo: RepositoryOverview | null; loading: boolean; error: string | null; onGoIssues: () => void;
}) {
  if (loading) return <LoadingSkeleton />;
  if (error) return <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10"><ErrorState title="Analysis failed" message={error} /></div>;
  if (!repo) return null;
  const langEntries = Object.entries(repo.detected_languages).sort((a, b) => b[1] - a[1]);
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6 animate-in">

      {/* Repo Identity Card */}
      <div className="card-brand">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-5">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <span className="w-9 h-9 rounded-2xl bg-brand-50 border border-brand-200/80 flex items-center justify-center text-brand-600 shadow-sm shrink-0">
                <IconGitHub className="w-5 h-5" />
              </span>
              <ExternalLink href={repo.github_url} className="text-xl sm:text-2xl font-extrabold text-gray-900 hover:text-brand-700 tracking-tight">
                {repo.full_name}
              </ExternalLink>
              {repo.archived && <span className="badge-warning">Archived</span>}
            </div>
            {repo.description && <p className="text-gray-600 text-sm mt-1 leading-relaxed">{repo.description}</p>}
            <div className="flex flex-wrap items-center gap-3 mt-4">
              <StatusIndicator status={repo.analysis_status} />
              {repo.commit_sha && (
                <span className="text-xs text-gray-500 font-mono bg-white border border-gray-200/80 px-2.5 py-0.5 rounded-lg shadow-sm">
                  @{repo.commit_sha.slice(0, 7)}
                </span>
              )}
              {repo.primary_language && <span className="badge-brand font-semibold">{repo.primary_language}</span>}
            </div>
          </div>
          <div className="flex flex-wrap gap-2.5 shrink-0">
            <StatChip icon={<IconStar className="w-4 h-4 text-amber-500" />} value={repo.stars.toLocaleString()} label="Stars" />
            <StatChip icon={<IconBranch className="w-4 h-4 text-brand-500" />} value={repo.forks.toLocaleString()} label="Forks" />
            <StatChip icon={<IconSearch className="w-4 h-4 text-purple-500" />} value={repo.open_issues_count} label="Open Issues" />
          </div>
        </div>
      </div>

      {repo.analysis_warnings.length > 0 && (
        <div className="notice-warning">
          <IconWarning className="shrink-0 mt-0.5 text-amber-600" />
          <div>
            <p className="font-bold mb-1">Analysis warnings</p>
            <ul className="text-xs space-y-1">{repo.analysis_warnings.map((w, i) => <li key={i}>&bull; {w}</li>)}</ul>
          </div>
        </div>
      )}

      {/* Languages & Frameworks Bento */}
      <div className="grid sm:grid-cols-2 gap-6">
        <div className="card p-6">
          <p className="section-label mb-4 text-brand-700">Languages Breakdown</p>
          {langEntries.length > 0 ? (
            <div className="space-y-3.5">
              {langEntries.slice(0, 6).map(([lang, pct]) => (
                <div key={lang}>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="font-semibold text-gray-800">{lang}</span>
                    <span className="text-gray-500 font-medium">{pct.toFixed(1)}%</span>
                  </div>
                  <ScoreBar score={pct / 100} />
                </div>
              ))}
            </div>
          ) : <p className="text-xs text-gray-400">No language data found</p>}
        </div>

        <div className="card p-6 space-y-5">
          {repo.detected_frameworks.length > 0 && (
            <div>
              <p className="section-label mb-2.5 text-purple-700">Detected Frameworks</p>
              <div className="flex flex-wrap gap-2">
                {repo.detected_frameworks.map((f) => (
                  <div key={f.name} className="flex items-center gap-1.5">
                    <span className="badge-brand font-semibold">{f.name}</span>
                    <span className="text-xs text-gray-400">({f.confidence})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {repo.config_files.length > 0 && (
            <div>
              <p className="section-label mb-2 text-indigo-700">Config Files</p>
              <div className="flex flex-wrap gap-1.5">
                {repo.config_files.slice(0, 10).map((f) => (
                  <span key={f} className="badge-muted font-mono text-[11px]">{f}</span>
                ))}
              </div>
            </div>
          )}
          {repo.test_locations.length > 0 && (
            <div>
              <p className="section-label mb-2 text-emerald-700">Test Directories</p>
              {repo.test_locations.map((t) => (
                <div key={t.path} className="flex items-center gap-2 text-xs text-gray-600 mt-1.5">
                  <IconFolder className="w-3.5 h-3.5 text-brand-500 shrink-0" />
                  <code className="text-gray-800 font-semibold">{t.path}</code>
                  {t.framework && <span className="text-gray-400">({t.framework})</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {repo.directory_snapshot.length > 0 && (
        <div className="card p-6">
          <p className="section-label mb-3 text-gray-700">Top-Level Directory Snapshot</p>
          <div className="flex flex-wrap gap-2">
            {repo.directory_snapshot.map((d) => (
              <span key={d} className="inline-flex items-center gap-1.5 badge-muted font-mono text-xs">
                <IconFolder className="w-3 h-3 text-brand-500" />{d}
              </span>
            ))}
          </div>
        </div>
      )}

      {repo.readme_summary && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="section-label text-gray-700">README Intelligence</p>
            <EvidenceBadge status="verified" />
          </div>
          <p className="text-sm text-gray-600 leading-relaxed italic bg-purple-50/40 p-4 rounded-2xl border border-purple-100/60">
            &ldquo;{repo.readme_summary}&rdquo;
          </p>
        </div>
      )}

      {repo.evidence_refs.length > 0 && (
        <div className="card p-6">
          <p className="section-label mb-4 text-gray-700">Evidence References ({repo.evidence_refs.length})</p>
          <div className="space-y-1">
            {repo.evidence_refs.map((ref) => (
              <div key={ref.id} className="flex items-start justify-between gap-3 text-xs py-2.5 border-b border-gray-100 last:border-0">
                <div className="flex-1">
                  <span className="text-purple-700 font-mono font-semibold">{ref.evidence_type.replace("_", " ")}</span>
                  {ref.file_path && <span className="text-gray-800 ml-2 font-mono font-medium">{ref.file_path}</span>}
                  {ref.excerpt && <p className="text-gray-500 mt-0.5 truncate">{ref.excerpt}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <EvidenceBadge status={ref.status} />
                  {ref.github_url && (
                    <a href={ref.github_url} target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:text-brand-800">
                      <IconExternal />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <button id="btn-go-issues" onClick={onGoIssues} className="btn-primary w-full justify-center py-4 text-base rounded-2xl shadow-lg">
        <IconSearch className="w-5 h-5" />Find Beginner-Friendly Issues to Contribute
      </button>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   IssuesView
───────────────────────────────────────────────────────────────────── */
function IssuesView({ issues, loading, error, onSelectIssue, owner, repo }: {
  issues: MatchedIssue[]; loading: boolean; error: string | null;
  onSelectIssue: (issue: MatchedIssue) => void; owner: string; repo: string;
}) {
  const [search, setSearch] = useState("");
  const [difficultyFilter, setDifficultyFilter] = useState<string>("all");
  const filtered = issues.filter((m) => {
    const matchSearch = !search || m.issue.title.toLowerCase().includes(search.toLowerCase()) ||
      m.issue.labels.some((l) => l.name.toLowerCase().includes(search.toLowerCase()));
    const matchDiff = difficultyFilter === "all" || m.difficulty === difficultyFilter;
    return matchSearch && matchDiff;
  });
  if (loading) return <LoadingSkeleton />;
  if (error) return <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10"><ErrorState title="Could not load issues" message={error} /></div>;
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 animate-in space-y-6">
      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <IconSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input id="issues-search" type="search" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search issues by title or label…" className="input pl-11" />
        </div>
        <select id="difficulty-filter" value={difficultyFilter} onChange={(e) => setDifficultyFilter(e.target.value)} className="input w-auto min-w-[170px]">
          <option value="all">All difficulties</option>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
          <option value="unknown">Unknown</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="No matching issues" description={issues.length === 0 ? `No open issues found in ${owner}/${repo}.` : "No issues match your current filters."} />
      ) : (
        <div className="space-y-4">
          {filtered.map((m) => <IssueCard key={m.issue.number} matched={m} onClick={() => onSelectIssue(m)} />)}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   IssueCard
───────────────────────────────────────────────────────────────────── */
function IssueCard({ matched, onClick }: { matched: MatchedIssue; onClick: () => void }) {
  const { issue, total_score, difficulty, difficulty_explanation, criteria, prerequisites, risks } = matched;
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="card-hover p-6">
      <div className="flex flex-col sm:flex-row gap-4 sm:items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-xs text-gray-400 font-mono font-bold">#{issue.number}</span>
            <DifficultyBadge level={difficulty} />
            {issue.labels.some(l => l.name.toLowerCase().includes("good first issue") || l.name.toLowerCase().includes("beginner")) && (
              <span className="badge-success">Good First Issue</span>
            )}
            {issue.labels.slice(0, 3).map((l) => <IssueLabel key={l.name} name={l.name} color={l.color} />)}
          </div>
          <h3 className="text-base font-bold text-gray-900 leading-snug mb-2">{issue.title}</h3>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>{new Date(issue.updated_at).toLocaleDateString()}</span>
            <span>&bull;</span>
            <span>{issue.comment_count} comments</span>
            {issue.author && (
              <>
                <span>&bull;</span>
                <span>by {issue.author}</span>
              </>
            )}
          </div>
        </div>
        <div className="shrink-0 sm:w-28 text-left sm:text-right bg-purple-50/60 sm:bg-transparent p-3 sm:p-0 rounded-2xl">
          <div className="text-2xl font-extrabold text-gradient mb-1">{Math.round(total_score * 100)}</div>
          <ScoreBar score={total_score} className="mb-1" />
          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">match score</p>
        </div>
      </div>

      <button onClick={() => setExpanded(!expanded)} className="mt-3.5 text-xs text-brand-600 hover:text-brand-800 transition-colors font-bold inline-flex items-center gap-1">
        <span>{expanded ? "Hide criteria details ↑" : "Show scoring criteria breakdown ↓"}</span>
      </button>

      {expanded && (
        <div className="mt-4 space-y-3 animate-in pt-4 border-t border-gray-100">
          {difficulty_explanation && (
            <div className="text-xs text-gray-600">
              <span className="font-bold text-gray-800">Difficulty evaluation: </span>{difficulty_explanation}
            </div>
          )}
          {prerequisites.length > 0 && (
            <div className="text-xs">
              <span className="font-bold text-gray-800">Prerequisites: </span>
              <span className="text-gray-600">{prerequisites.join(", ")}</span>
            </div>
          )}
          {risks.length > 0 && (
            <div className="text-xs">
              <span className="font-bold text-amber-700">Risks &amp; Pitfalls: </span>
              <span className="text-gray-600">{risks.join(", ")}</span>
            </div>
          )}
          <div className="space-y-2 pt-2">
            <p className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Criteria Breakdown (7 Factors)</p>
            {criteria.map((c) => (
              <div key={c.name} className="flex items-start gap-2.5 text-xs bg-white/70 p-2 rounded-xl border border-gray-100">
                <span className={`mt-0.5 shrink-0 font-bold ${c.passed ? "text-emerald-600" : "text-rose-500"}`}>
                  {c.passed ? "✓" : "✗"}
                </span>
                <div className="flex-1">
                  <span className="text-gray-700">{c.explanation}</span>
                  {c.missing_data && <span className="ml-1.5 badge-warning text-[10px]">Missing data</span>}
                </div>
                <span className="text-gray-500 font-mono font-bold shrink-0">{Math.round(c.score * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3 mt-5 pt-4 border-t border-gray-100">
        <button id={`btn-plan-${issue.number}`} onClick={onClick} className="btn-primary text-xs py-2 px-4 rounded-xl">
          <IconSparkle className="w-3.5 h-3.5" />Generate Plan
        </button>
        <a href={issue.github_url} target="_blank" rel="noopener noreferrer" className="btn-secondary text-xs py-2 px-4 rounded-xl inline-flex items-center gap-1.5">
          View on GitHub<IconExternal className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   PlanView
───────────────────────────────────────────────────────────────────── */
function PlanView({ plan, loading, error }: { plan: ContributionPlan | null; loading: boolean; error: string | null; }) {
  if (loading) return <LoadingSkeleton />;
  if (error) return <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10"><ErrorState title="Could not generate plan" message={error} /></div>;
  if (!plan) return <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10"><EmptyState title="No plan generated yet" description="Select an issue from the Issues tab to generate a contribution plan." /></div>;
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6 animate-in">
      <div className="card-brand">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <p className="section-label mb-2 text-brand-700">Evidence-Backed Contribution Plan</p>
            <h2 className="text-xl sm:text-2xl font-extrabold text-gray-900 leading-tight">
              Issue #{plan.issue_number}: {plan.issue_title}
            </h2>
            <ExternalLink href={plan.issue_url} className="text-xs mt-2 block font-semibold text-brand-600">
              View original issue on GitHub
            </ExternalLink>
          </div>
          <div className="shrink-0">
            {plan.ai_generated ? (
              <span className="badge-brand flex items-center gap-1.5 text-xs font-bold py-1 px-3">
                <IconSparkle className="w-3.5 h-3.5" /> AI Enriched
              </span>
            ) : <span className="badge-muted text-xs font-semibold py-1 px-3">Deterministic AST</span>}
          </div>
        </div>
        <p className="mt-5 text-sm text-gray-600 leading-relaxed bg-white/70 p-4 rounded-2xl border border-brand-100">
          {plan.summary}
        </p>
      </div>

      {(plan.uncertainties.length > 0 || plan.assumptions.length > 0) && (
        <div className="notice-warning">
          <IconWarning className="shrink-0 mt-0.5 text-amber-600" />
          <div>
            <p className="font-bold mb-2">Important Caveats &amp; Assumptions</p>
            {plan.uncertainties.map((u, i) => <p key={i} className="text-xs mb-1">&bull; {u}</p>)}
            {plan.assumptions.map((a, i) => <p key={i} className="text-xs mb-1 text-amber-800">~ {a}</p>)}
          </div>
        </div>
      )}

      {/* Step-by-step roadmap */}
      <div className="card p-6 sm:p-8">
        <p className="section-label mb-5 text-purple-700">Implementation Steps</p>
        <ol className="space-y-6">
          {plan.implementation_steps.map((step) => (
            <li key={step.order} className="flex gap-4">
              <div className="w-8 h-8 rounded-2xl flex items-center justify-center text-white text-xs font-extrabold shrink-0 shadow-md"
                style={{ background: "linear-gradient(135deg, #6366f1 0%, #7c3aed 100%)" }}>
                {step.order}
              </div>
              <div className="flex-1 pt-0.5">
                <p className="text-sm font-bold text-gray-900">{step.description}</p>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">{step.rationale}</p>
                {step.relevant_files.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {step.relevant_files.map((f) => (
                      <span key={f} className="badge-muted font-mono text-[11px]">{f}</span>
                    ))}
                  </div>
                )}
                {!step.is_verified && (
                  <span className="mt-2 inline-block badge-warning text-[10px]">
                    Not verified against live AST &mdash; verify manually
                  </span>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="grid sm:grid-cols-2 gap-6">
        {plan.prerequisite_concepts.length > 0 && (
          <div className="card p-6">
            <p className="section-label mb-4 text-brand-700">Prerequisites &amp; Concepts</p>
            <ul className="space-y-2.5">
              {plan.prerequisite_concepts.map((c, i) => (
                <li key={i} className="flex items-center gap-2.5 text-sm text-gray-700">
                  <span className="w-2 h-2 rounded-full bg-brand-500 shrink-0" />
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}
        {plan.suggested_tests.length > 0 && (
          <div className="card p-6">
            <p className="section-label mb-4 text-emerald-700">Suggested Verification Tests</p>
            <ul className="space-y-2.5">
              {plan.suggested_tests.map((t, i) => (
                <li key={i} className="text-xs text-gray-600 leading-relaxed flex gap-2">
                  <span className="text-emerald-600 font-bold mt-0.5 shrink-0">&bull;</span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {plan.relevant_files.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <p className="section-label text-gray-700">Possibly Relevant Files</p>
            <span className="badge-warning text-[10px]">Keyword match &mdash; verify manually</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {plan.relevant_files.map((f) => <span key={f} className="badge-muted font-mono text-xs">{f}</span>)}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   SettingsView
───────────────────────────────────────────────────────────────────── */
function SettingsView({ health, healthLoading }: { health: HealthResponse | null; healthLoading: boolean }) {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6 animate-in">
      <div>
        <h2 className="text-2xl font-extrabold text-gray-900 mb-1">Settings &amp; System Health</h2>
        <p className="text-sm text-gray-500">Service health and configuration. No secrets or private tokens are shown.</p>
      </div>
      <div className="card p-6">
        <p className="section-label mb-4 text-gray-700">Backend Service Status</p>
        {healthLoading ? (
          <div className="space-y-3"><Skeleton className="w-3/4 h-5" /><Skeleton className="w-1/2 h-5" /><Skeleton className="w-2/3 h-5" /></div>
        ) : health ? (
          <div className="space-y-0.5">
            {[
              { label: "Status",      value: health.status === "ok" ? "✓ Operational" : "✗ Error" },
              { label: "Version",     value: health.version },
              { label: "Environment", value: health.environment },
              { label: "AI Provider", value: health.ai_provider },
              { label: "AI Status",   value: health.ai_provider_status },
              { label: "GitHub Auth", value: health.github_authenticated ? "Authenticated" : "Unauthenticated (60 req/hr)" },
            ].map((row) => (
              <div key={row.label} className="flex justify-between items-center py-3 border-b border-gray-100 last:border-0">
                <span className="text-sm text-gray-500 font-medium">{row.label}</span>
                <span className={`font-mono text-xs font-bold ${row.label === "AI Status" && health.ai_provider_status === "not_configured" ? "text-gray-400" : row.label === "AI Status" && health.ai_provider_status === "available" ? "text-emerald-600" : "text-gray-800"}`}>{row.value}</span>
              </div>
            ))}
          </div>
        ) : <ErrorState message="Could not connect to backend. Is it running on localhost:8000?" />}
      </div>
      <div className="notice-info">
        <IconInfo className="shrink-0 mt-0.5 text-sky-600" />
        <div className="text-xs space-y-1.5">
          <p className="font-bold text-sm text-sky-900">AI Provider Configuration</p>
          <p>To enable AI enrichment, set <code className="font-mono bg-sky-100/80 px-1.5 py-0.5 rounded text-sky-900">AI_PROVIDER</code> in your backend <code className="font-mono bg-sky-100/80 px-1.5 py-0.5 rounded text-sky-900">.env</code> file.</p>
          <p>Supported: <code className="font-mono text-sky-900 font-semibold">google_ai_studio</code>, <code className="font-mono text-sky-900 font-semibold">local_ollama</code>.</p>
          <p>See <code className="font-mono text-sky-900">.env.example</code> for all required variables.</p>
          <p className="text-sky-700/80">The application remains fully deterministic and functional without AI.</p>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   LoadingSkeleton
───────────────────────────────────────────────────────────────────── */
function LoadingSkeleton() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-5" aria-busy="true" aria-label="Loading…">
      <div className="card p-8 space-y-4"><Skeleton className="w-1/3 h-7" /><Skeleton className="w-2/3 h-5" /><Skeleton className="w-1/2 h-4" /></div>
      <div className="grid sm:grid-cols-2 gap-5">
        <div className="card p-6 space-y-3">{[1,2,3,4].map((i) => <Skeleton key={i} className={`w-${["3/4","1/2","2/3","1/3"][i-1]} h-4`} />)}</div>
        <div className="card p-6 space-y-3">{[1,2,3].map((i) => <Skeleton key={i} className="w-full h-4" />)}</div>
      </div>
      <div className="card p-6 space-y-3">{[1,2,3,4,5].map((i) => <Skeleton key={i} className="w-full h-4" />)}</div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   App (root)
───────────────────────────────────────────────────────────────────── */
export default function App() {
  const [view, setView]                   = useState<View>("home");
  const [repoOverview, setRepoOverview]   = useState<RepositoryOverview | null>(null);
  const [repoLoading, setRepoLoading]     = useState(false);
  const [repoError, setRepoError]         = useState<string | null>(null);
  const [issues, setIssues]               = useState<MatchedIssue[]>([]);
  const [issuesLoading, setIssuesLoading] = useState(false);
  const [issuesError, setIssuesError]     = useState<string | null>(null);
  const [plan, setPlan]                   = useState<ContributionPlan | null>(null);
  const [planLoading, setPlanLoading]     = useState(false);
  const [planError, setPlanError]         = useState<string | null>(null);
  const [health, setHealth]               = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  React.useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null)).finally(() => setHealthLoading(false));
  }, []);

  const handleAnalyze = useCallback(async (url: string) => {
    setRepoError(null); setRepoLoading(true); setView("overview");
    try {
      const result = await api.analyzeRepository(url);
      setRepoOverview(result.repository); setIssues([]); setPlan(null);
    } catch (err) {
      const msg = err instanceof APIError
        ? `${err.message}${err.detail ? ` — ${JSON.stringify(err.detail)}` : ""}`
        : "An unexpected error occurred. Is the backend running?";
      setRepoError(msg); setView("overview");
    } finally { setRepoLoading(false); }
  }, []);

  const handleGoIssues = useCallback(async () => {
    if (!repoOverview) return;
    setView("issues");
    if (issues.length > 0) return;
    setIssuesLoading(true); setIssuesError(null);
    try {
      const result = await api.matchIssues({
        owner: repoOverview.identity.owner,
        repo:  repoOverview.identity.repo,
        skills: [],
        preferred_languages: repoOverview.primary_language ? [repoOverview.primary_language] : [],
        experience_level: "beginner",
        learning_preferences: [],
      });
      setIssues(result.matched_issues);
    } catch (err) { setIssuesError(err instanceof APIError ? err.message : "Failed to load issues"); }
    finally { setIssuesLoading(false); }
  }, [repoOverview, issues.length]);

  const handleSelectIssue = useCallback(async (matched: MatchedIssue) => {
    if (!repoOverview) return;
    setView("plan"); setPlanLoading(true); setPlanError(null);
    try {
      const result = await api.generatePlan(repoOverview.identity.owner, repoOverview.identity.repo, matched.issue.number);
      setPlan(result);
    } catch (err) { setPlanError(err instanceof APIError ? err.message : "Failed to generate plan"); }
    finally { setPlanLoading(false); }
  }, [repoOverview]);

  return (
    <div className="min-h-screen flex flex-col">
      <Nav view={view} setView={setView} hasRepo={!!repoOverview} health={health} />
      <div className="flex-1">
        {view === "home"     && <HomeView onAnalyze={handleAnalyze} />}
        {view === "overview" && <OverviewView repo={repoOverview} loading={repoLoading} error={repoError} onGoIssues={handleGoIssues} />}
        {view === "issues"   && <IssuesView issues={issues} loading={issuesLoading} error={issuesError} onSelectIssue={handleSelectIssue} owner={repoOverview?.identity.owner ?? ""} repo={repoOverview?.identity.repo ?? ""} />}
        {view === "plan"     && <PlanView plan={plan} loading={planLoading} error={planError} />}
        {view === "settings" && <SettingsView health={health} healthLoading={healthLoading} />}
      </div>
      <footer className="border-t border-gray-200/70 py-6 text-center bg-white/40 backdrop-blur-sm">
        <p className="text-xs text-gray-500 font-medium">
          FirstPatch AI &bull; Evidence-backed open-source mentorship &bull; v0.1.0
        </p>
      </footer>
    </div>
  );
}
