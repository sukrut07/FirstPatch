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
  ScoreBar,
  DifficultyBadge,
  EvidenceBadge,
  StatusIndicator,
  Skeleton,
  EmptyState,
  ErrorState,
  ExternalLink,
  IssueLabel,
} from "@/components/ui";
import { VerificationPanel } from "@/components/VerificationPanel";

// ---------------------------------------------------------------------------
// View State Machine
// ---------------------------------------------------------------------------
type View = "home" | "overview" | "issues" | "plan" | "settings";

// ---------------------------------------------------------------------------
// App Shell / Nav
// ---------------------------------------------------------------------------
function Nav({
  view,
  setView,
  hasRepo,
  health,
}: {
  view: View;
  setView: (v: View) => void;
  hasRepo: boolean;
  health: HealthResponse | null;
}) {
  const navItems: { key: View; label: string; disabled?: boolean }[] = [
    { key: "home",     label: "Analyze" },
    { key: "overview", label: "Overview",      disabled: !hasRepo },
    { key: "issues",   label: "Issues",         disabled: !hasRepo },
    { key: "plan",     label: "Plan",            disabled: !hasRepo },
    { key: "settings", label: "Settings" },
  ];

  return (
    <nav className="border-b border-white/[0.06] bg-surface-900/80 backdrop-blur-sm sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-4 flex items-center gap-6 h-14">
        {/* Logo */}
        <button
          onClick={() => setView("home")}
          className="flex items-center gap-2.5 text-sm font-bold tracking-tight shrink-0"
          id="nav-logo"
        >
          <span className="w-7 h-7 rounded-lg bg-brand-gradient flex items-center justify-center text-white text-xs font-black">
            FP
          </span>
          <span className="text-gradient hidden sm:block">FirstPatch AI</span>
        </button>

        {/* Nav items */}
        <div className="flex items-center gap-1 flex-1">
          {navItems.map((item) => (
            <button
              key={item.key}
              id={`nav-${item.key}`}
              disabled={item.disabled}
              onClick={() => setView(item.key)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-150
                ${view === item.key
                  ? "bg-brand-600/20 text-brand-300 border border-brand-500/30"
                  : item.disabled
                    ? "text-gray-600 cursor-not-allowed"
                    : "text-gray-400 hover:text-gray-200 hover:bg-surface-800"
                }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* AI status pill */}
        {health && (
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-gray-500">
            <span className={`w-1.5 h-1.5 rounded-full ${
              health.ai_provider_status === "available"     ? "bg-status-success" :
              health.ai_provider_status === "degraded"      ? "bg-status-warning animate-pulse" :
              health.ai_provider_status === "not_configured"? "bg-gray-600" :
              "bg-status-error"
            }`} />
            {health.ai_provider_status === "not_configured" ? "AI: Off" :
             health.ai_provider_status === "available"      ? `AI: ${health.ai_provider}` :
             "AI: Unavailable"}
          </div>
        )}
      </div>
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Home View
// ---------------------------------------------------------------------------
function HomeView({
  onAnalyze,
}: {
  onAnalyze: (url: string) => void;
}) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function validateURL(value: string): string {
    if (!value.trim()) return "Please enter a GitHub repository URL";
    if (!value.includes("github.com")) return "Only GitHub repositories are supported";
    const parts = value.replace(/^https?:\/\//, "").replace(/^github\.com\//, "").split("/");
    if (parts.length < 2 || !parts[0] || !parts[1]) {
      return "URL must include owner and repository name (e.g. github.com/owner/repo)";
    }
    return "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validateURL(url);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError("");
    setLoading(true);
    try {
      await onAnalyze(url);
    } finally {
      setLoading(false);
    }
  }

  const demoRepos = [
    { label: "facebook/react", url: "https://github.com/facebook/react" },
    { label: "tiangolo/fastapi", url: "https://github.com/tiangolo/fastapi" },
    { label: "vercel/next.js", url: "https://github.com/vercel/next.js" },
    { label: "microsoft/vscode", url: "https://github.com/microsoft/vscode" },
  ];

  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-24 animate-in">
      {/* Hero */}
      <div className="text-center mb-12 max-w-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-medium mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse-slow" />
          Open-source contribution mentor
        </div>
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-5 leading-tight">
          Make your{" "}
          <span className="text-gradient glow-brand">first patch</span>
          <br />with confidence
        </h1>
        <p className="text-lg text-gray-400 leading-relaxed">
          Enter a public GitHub repository URL. FirstPatch AI analyzes its structure,
          finds beginner-friendly issues, and builds you a step-by-step contribution
          plan backed by real evidence — not guesswork.
        </p>
      </div>

      {/* URL Input */}
      <form onSubmit={handleSubmit} className="w-full max-w-xl" noValidate>
        <div className="card-brand p-6">
          <label htmlFor="repo-url" className="section-label block mb-3">
            GitHub Repository URL
          </label>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <IconGitHub className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                id="repo-url"
                ref={inputRef}
                type="url"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  if (error) setError(validateURL(e.target.value));
                }}
                placeholder="https://github.com/owner/repository"
                className={`input pl-9 ${error ? "border-status-error/50 ring-status-error/20" : ""}`}
                disabled={loading}
                autoComplete="off"
                autoFocus
                aria-describedby={error ? "url-error" : undefined}
                aria-invalid={!!error}
              />
            </div>
            <button
              id="btn-analyze"
              type="submit"
              disabled={loading || !url.trim()}
              className="btn-primary shrink-0"
            >
              {loading ? <IconSpinner /> : <IconSearch />}
              {loading ? "Analyzing…" : "Analyze"}
            </button>
          </div>
          {error && (
            <p id="url-error" className="mt-2 text-xs text-status-error flex items-center gap-1" role="alert">
              <IconWarning className="w-3 h-3 shrink-0" />
              {error}
            </p>
          )}
        </div>

        {/* Quick-pick repos */}
        <div className="mt-4">
          <p className="text-xs text-gray-600 mb-2 text-center">Try a demo repository:</p>
          <div className="flex flex-wrap gap-2 justify-center">
            {demoRepos.map((r) => (
              <button
                key={r.url}
                type="button"
                onClick={() => { setUrl(r.url); setError(""); }}
                className="btn-secondary text-xs py-1 px-3"
                id={`demo-${r.label.replace("/", "-")}`}
              >
                <IconGitHub className="w-3 h-3" />
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </form>

      {/* Features */}
      <div className="mt-20 grid sm:grid-cols-3 gap-4 max-w-3xl w-full">
        {[
          {
            icon: "🔍",
            title: "Evidence-backed analysis",
            desc: "Every displayed fact is traced to a real source — no invented file paths or issue statuses.",
          },
          {
            icon: "📋",
            title: "Transparent matching",
            desc: "Issues are ranked by 7 explicit criteria with visible scores and honest explanations.",
          },
          {
            icon: "🗺️",
            title: "Step-by-step plans",
            desc: "Get an ordered contribution plan with listed uncertainties and explicit assumptions.",
          },
        ].map((f) => (
          <div key={f.title} className="card p-5 text-center">
            <div className="text-3xl mb-3">{f.icon}</div>
            <h3 className="text-sm font-semibold text-gray-200 mb-2">{f.title}</h3>
            <p className="text-xs text-gray-500 leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Overview View
// ---------------------------------------------------------------------------
function OverviewView({
  repo,
  loading,
  error,
  onGoIssues,
}: {
  repo: RepositoryOverview | null;
  loading: boolean;
  error: string | null;
  onGoIssues: () => void;
}) {
  if (loading) return <LoadingSkeleton />;
  if (error) return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <ErrorState title="Analysis failed" message={error} />
    </div>
  );
  if (!repo) return null;

  const langEntries = Object.entries(repo.detected_languages).sort((a, b) => b[1] - a[1]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <IconGitHub className="w-6 h-6 text-gray-400" />
            <ExternalLink href={repo.github_url} className="text-xl font-bold text-white hover:text-brand-300">
              {repo.full_name}
            </ExternalLink>
            {repo.archived && <span className="badge-warning">Archived</span>}
          </div>
          {repo.description && (
            <p className="text-gray-400 text-sm mt-1">{repo.description}</p>
          )}
          <div className="flex flex-wrap gap-3 mt-3">
            <StatusIndicator status={repo.analysis_status} />
            {repo.commit_sha && (
              <span className="text-xs text-gray-600 font-mono">
                @{repo.commit_sha.slice(0, 7)}
              </span>
            )}
            {repo.primary_language && (
              <span className="badge-brand">{repo.primary_language}</span>
            )}
          </div>
        </div>
        <div className="flex gap-4 text-sm text-gray-500 shrink-0">
          <span className="flex items-center gap-1.5"><IconStar className="text-amber-400" />{repo.stars.toLocaleString()}</span>
          <span className="flex items-center gap-1.5"><IconBranch className="text-gray-500" />{repo.forks.toLocaleString()}</span>
          <span className="text-gray-500">{repo.open_issues_count} open issues</span>
        </div>
      </div>

      {/* Warnings */}
      {repo.analysis_warnings.length > 0 && (
        <div className="notice-warning">
          <IconWarning className="shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold mb-1">Analysis warnings</p>
            <ul className="text-xs space-y-1">
              {repo.analysis_warnings.map((w, i) => <li key={i}>• {w}</li>)}
            </ul>
          </div>
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-4">
        {/* Languages */}
        <div className="card p-5">
          <p className="section-label mb-3">Languages</p>
          {langEntries.length > 0 ? (
            <div className="space-y-2.5">
              {langEntries.slice(0, 6).map(([lang, pct]) => (
                <div key={lang}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-300">{lang}</span>
                    <span className="text-gray-500">{pct.toFixed(1)}%</span>
                  </div>
                  <ScoreBar score={pct / 100} />
                </div>
              ))}
            </div>
          ) : <p className="text-xs text-gray-600">No language data available</p>}
        </div>

        {/* Frameworks & Config */}
        <div className="card p-5 space-y-4">
          {repo.detected_frameworks.length > 0 && (
            <div>
              <p className="section-label mb-3">Detected Frameworks</p>
              <div className="flex flex-wrap gap-2">
                {repo.detected_frameworks.map((f) => (
                  <div key={f.name} className="flex items-center gap-1.5">
                    <span className="badge-brand">{f.name}</span>
                    <span className="text-xs text-gray-600">{f.confidence}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {repo.config_files.length > 0 && (
            <div>
              <p className="section-label mb-2">Config Files</p>
              <div className="flex flex-wrap gap-1">
                {repo.config_files.slice(0, 10).map((f) => (
                  <span key={f} className="badge-muted font-mono text-xs">{f}</span>
                ))}
              </div>
            </div>
          )}
          {repo.test_locations.length > 0 && (
            <div>
              <p className="section-label mb-2">Test Directories</p>
              {repo.test_locations.map((t) => (
                <div key={t.path} className="flex items-center gap-2 text-xs text-gray-400">
                  <IconFolder className="w-3 h-3 text-gray-600" />
                  <code className="text-gray-300">{t.path}</code>
                  {t.framework && <span className="text-gray-600">({t.framework})</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Directory snapshot */}
      {repo.directory_snapshot.length > 0 && (
        <div className="card p-5">
          <p className="section-label mb-3">Top-Level Directory</p>
          <div className="flex flex-wrap gap-1.5">
            {repo.directory_snapshot.map((d) => (
              <span key={d} className="inline-flex items-center gap-1 badge-muted font-mono text-xs">
                <IconFolder className="w-3 h-3 text-gray-600" />
                {d}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* README excerpt */}
      {repo.readme_summary && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="section-label">README Excerpt</p>
            <EvidenceBadge status="verified" />
          </div>
          <p className="text-sm text-gray-400 leading-relaxed italic">&ldquo;{repo.readme_summary}&rdquo;</p>
        </div>
      )}

      {/* Evidence refs */}
      {repo.evidence_refs.length > 0 && (
        <div className="card p-5">
          <p className="section-label mb-3">Evidence References ({repo.evidence_refs.length})</p>
          <div className="space-y-2">
            {repo.evidence_refs.map((ref) => (
              <div key={ref.id} className="flex items-start justify-between gap-3 text-xs py-2 border-b border-white/[0.04] last:border-0">
                <div className="flex-1">
                  <span className="text-gray-500 font-mono">{ref.evidence_type.replace("_", " ")}</span>
                  {ref.file_path && <span className="text-gray-400 ml-2 font-mono">{ref.file_path}</span>}
                  {ref.excerpt && <p className="text-gray-600 mt-0.5 truncate">{ref.excerpt}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <EvidenceBadge status={ref.status} />
                  {ref.github_url && (
                    <a href={ref.github_url} target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:text-brand-400">
                      <IconExternal />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Isolated Verification */}
      <VerificationPanel repo={repo} />

      <button id="btn-go-issues" onClick={onGoIssues} className="btn-primary w-full justify-center py-3">
        <IconSearch />
        Find Issues to Contribute
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Issues View
// ---------------------------------------------------------------------------
function IssuesView({
  issues,
  loading,
  error,
  onSelectIssue,
  owner,
  repo,
}: {
  issues: MatchedIssue[];
  loading: boolean;
  error: string | null;
  onSelectIssue: (issue: MatchedIssue) => void;
  owner: string;
  repo: string;
}) {
  const [search, setSearch] = useState("");
  const [difficultyFilter, setDifficultyFilter] = useState<string>("all");

  const filtered = issues.filter((m) => {
    const matchSearch =
      !search ||
      m.issue.title.toLowerCase().includes(search.toLowerCase()) ||
      m.issue.labels.some((l) => l.name.toLowerCase().includes(search.toLowerCase()));
    const matchDiff = difficultyFilter === "all" || m.difficulty === difficultyFilter;
    return matchSearch && matchDiff;
  });

  if (loading) return <LoadingSkeleton />;
  if (error) return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <ErrorState title="Could not load issues" message={error} />
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 animate-in">
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="flex-1 relative">
          <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            id="issues-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search issues by title or label…"
            className="input pl-9"
          />
        </div>
        <select
          id="difficulty-filter"
          value={difficultyFilter}
          onChange={(e) => setDifficultyFilter(e.target.value)}
          className="input w-auto min-w-[160px]"
        >
          <option value="all">All difficulties</option>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
          <option value="unknown">Unknown</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No matching issues"
          description={
            issues.length === 0
              ? `No open issues found in ${owner}/${repo}.`
              : "No issues match your current filters."
          }
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((m) => (
            <IssueCard
              key={m.issue.number}
              matched={m}
              onClick={() => onSelectIssue(m)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function IssueCard({ matched, onClick }: { matched: MatchedIssue; onClick: () => void }) {
  const { issue, total_score, difficulty, difficulty_explanation, criteria, prerequisites, risks } = matched;
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="card-hover p-5">
      <div className="flex gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-xs text-gray-600 font-mono">#{issue.number}</span>
            <DifficultyBadge level={difficulty} />
            {issue.labels.some(l => l.name.toLowerCase().includes("good first issue") || l.name.toLowerCase().includes("beginner")) && <span className="badge-success">Good First Issue</span>}
            {issue.labels.slice(0, 3).map((l) => (
              <IssueLabel key={l.name} name={l.name} color={l.color} />
            ))}
          </div>
          <h3 className="text-sm font-semibold text-gray-200 leading-tight mb-2">
            {issue.title}
          </h3>
          <div className="flex items-center gap-4 text-xs text-gray-600">
            <span>{new Date(issue.updated_at).toLocaleDateString()}</span>
            <span>{issue.comment_count} comments</span>
            {issue.author && <span>by {issue.author}</span>}
          </div>
        </div>
        <div className="shrink-0 w-24 text-right">
          <div className="text-lg font-bold text-brand-400 mb-1">
            {Math.round(total_score * 100)}
          </div>
          <ScoreBar score={total_score} className="mb-1" />
          <p className="text-xs text-gray-600">match score</p>
        </div>
      </div>

      {/* Criteria (collapsible) */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        {expanded ? "Hide criteria ↑" : "Show scoring criteria ↓"}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 animate-in pt-2 border-t border-white/[0.04]">
          {difficulty_explanation && (
            <div className="text-xs text-gray-400">
              <span className="font-semibold text-gray-300">Difficulty assessment: </span>
              {difficulty_explanation}
            </div>
          )}
          {prerequisites.length > 0 && (
            <div className="text-xs">
              <span className="font-semibold text-gray-300">Prerequisites: </span>
              <span className="text-gray-400">{prerequisites.join(", ")}</span>
            </div>
          )}
          {risks.length > 0 && (
            <div className="text-xs">
              <span className="font-semibold text-amber-400/90">Risks / Watch out: </span>
              <span className="text-gray-400">{risks.join(", ")}</span>
            </div>
          )}
          <div className="space-y-1.5 pt-1">
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Criteria Breakdown</p>
            {criteria.map((c) => (
              <div key={c.name} className="flex items-start gap-2 text-xs">
                <span className={`mt-0.5 shrink-0 ${c.passed ? "text-status-success" : "text-status-error"}`}>
                  {c.passed ? "✓" : "✗"}
                </span>
                <div className="flex-1">
                  <span className="text-gray-400">{c.explanation}</span>
                  {c.missing_data && <span className="ml-1 badge-warning text-[10px]">Missing data</span>}
                </div>
                <span className="text-gray-600 font-mono shrink-0">{Math.round(c.score * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 mt-4 pt-4 border-t border-white/[0.04]">
        <button
          id={`btn-plan-${issue.number}`}
          onClick={onClick}
          className="btn-primary text-xs py-1.5"
        >
          Generate Plan
        </button>
        <a
          href={issue.github_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary text-xs py-1.5 inline-flex items-center gap-1"
        >
          View on GitHub
          <IconExternal />
        </a>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Plan View
// ---------------------------------------------------------------------------
function PlanView({
  plan,
  repo,
  loading,
  error,
}: {
  plan: ContributionPlan | null;
  repo: RepositoryOverview | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <LoadingSkeleton />;
  if (error) return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <ErrorState title="Could not generate plan" message={error} />
    </div>
  );
  if (!plan) return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <EmptyState
        title="No plan generated yet"
        description="Select an issue from the Issues tab to generate a contribution plan."
      />
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6 animate-in">
      {/* Header */}
      <div className="card-brand p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="section-label mb-2">Contribution Plan</p>
            <h2 className="text-lg font-bold text-gray-100 leading-tight">
              Issue #{plan.issue_number}: {plan.issue_title}
            </h2>
            <ExternalLink href={plan.issue_url} className="text-xs mt-2 block">
              View original issue
            </ExternalLink>
          </div>
          <div className="shrink-0">
            {plan.ai_generated ? (
              <span className="badge-brand">AI Enriched</span>
            ) : (
              <span className="badge-muted">Deterministic</span>
            )}
          </div>
        </div>
        <p className="mt-4 text-sm text-gray-400 leading-relaxed">{plan.summary}</p>
      </div>

      {/* Assumptions & Uncertainties */}
      {(plan.uncertainties.length > 0 || plan.assumptions.length > 0) && (
        <div className="notice-warning">
          <IconWarning className="shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold mb-2">Important Caveats</p>
            {plan.uncertainties.map((u, i) => (
              <p key={i} className="text-xs mb-1">⚠ {u}</p>
            ))}
            {plan.assumptions.map((a, i) => (
              <p key={i} className="text-xs mb-1 text-amber-300/70">~ {a}</p>
            ))}
          </div>
        </div>
      )}

      {/* Implementation Steps */}
      <div className="card p-5">
        <p className="section-label mb-4">Implementation Steps</p>
        <ol className="space-y-4">
          {plan.implementation_steps.map((step) => (
            <li key={step.order} className="flex gap-4">
              <div className="w-7 h-7 rounded-lg bg-brand-600/20 border border-brand-500/30 flex items-center justify-center text-brand-300 text-xs font-bold shrink-0">
                {step.order}
              </div>
              <div className="flex-1 pt-0.5">
                <p className="text-sm font-medium text-gray-200">{step.description}</p>
                <p className="text-xs text-gray-500 mt-1">{step.rationale}</p>
                {step.relevant_files.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {step.relevant_files.map((f) => (
                      <span key={f} className="badge-muted font-mono text-xs">{f}</span>
                    ))}
                  </div>
                )}
                {!step.is_verified && (
                  <span className="mt-1 badge-warning text-[10px]">Not verified against live code</span>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {/* Prerequisites */}
        {plan.prerequisite_concepts.length > 0 && (
          <div className="card p-5">
            <p className="section-label mb-3">Prerequisites</p>
            <ul className="space-y-1.5">
              {plan.prerequisite_concepts.map((c, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-gray-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-500 shrink-0" />
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Suggested Tests */}
        {plan.suggested_tests.length > 0 && (
          <div className="card p-5">
            <p className="section-label mb-3">Suggested Tests</p>
            <ul className="space-y-2">
              {plan.suggested_tests.map((t, i) => (
                <li key={i} className="text-xs text-gray-400 leading-relaxed">
                  • {t}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Relevant Files */}
      {plan.relevant_files.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="section-label">Possibly Relevant Files</p>
            <span className="badge-warning text-[10px]">Keyword match — verify manually</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {plan.relevant_files.map((f) => (
              <span key={f} className="badge-muted font-mono text-xs">{f}</span>
            ))}
          </div>
        </div>
      )}

      {/* Isolated Test Verification */}
      {repo && <VerificationPanel repo={repo} plan={plan} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Settings View
// ---------------------------------------------------------------------------
function SettingsView({ health, healthLoading }: { health: HealthResponse | null; healthLoading: boolean }) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6 animate-in">
      <div>
        <h2 className="text-xl font-bold text-gray-100 mb-1">Settings & Status</h2>
        <p className="text-sm text-gray-500">Service health and configuration. No secrets are displayed here.</p>
      </div>

      <div className="card p-5">
        <p className="section-label mb-4">Service Health</p>
        {healthLoading ? (
          <div className="space-y-2">
            <Skeleton className="w-3/4" />
            <Skeleton className="w-1/2" />
          </div>
        ) : health ? (
          <div className="space-y-3 text-sm">
            {[
              { label: "Status",         value: health.status === "ok" ? "✓ OK" : "✗ Error", ok: health.status === "ok" },
              { label: "Version",        value: health.version },
              { label: "Environment",    value: health.environment },
              { label: "AI Provider",    value: health.ai_provider },
              { label: "AI Status",      value: health.ai_provider_status },
              { label: "GitHub Auth",    value: health.github_authenticated ? "Authenticated" : "Unauthenticated (60 req/hr)" },
            ].map((row) => (
              <div key={row.label} className="flex justify-between items-center py-2 border-b border-white/[0.04] last:border-0">
                <span className="text-gray-500">{row.label}</span>
                <span className={`font-mono text-xs ${
                  row.label === "AI Status" && health.ai_provider_status === "not_configured"
                    ? "text-gray-500"
                    : row.label === "AI Status" && health.ai_provider_status === "available"
                      ? "text-status-success"
                      : "text-gray-300"
                }`}>
                  {row.value}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <ErrorState message="Could not connect to backend. Is it running on localhost:8000?" />
        )}
      </div>

      <div className="notice-info">
        <IconInfo className="shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold">AI Provider Configuration</p>
          <p>To enable AI enrichment, set <code className="font-mono bg-surface-700 px-1 rounded">AI_PROVIDER</code> in your backend <code className="font-mono bg-surface-700 px-1 rounded">.env</code> file.</p>
          <p>Supported providers: <code className="font-mono">google_ai_studio</code> (Gemma via Google AI Studio), <code className="font-mono">local_ollama</code> (local Gemma via Ollama).</p>
          <p>See <code className="font-mono">.env.example</code> for all required variables.</p>
          <p className="text-blue-300/60">The application remains fully functional for repository exploration without AI.</p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading Skeleton
// ---------------------------------------------------------------------------
function LoadingSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-4" aria-busy="true" aria-label="Loading…">
      <div className="card p-6 space-y-3">
        <Skeleton className="w-1/3 h-6" />
        <Skeleton className="w-2/3" />
        <Skeleton className="w-1/2" />
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="card p-5 space-y-2">
          {[1,2,3,4].map((i) => <Skeleton key={i} className={`w-${["3/4","1/2","2/3","1/3"][i-1]}`} />)}
        </div>
        <div className="card p-5 space-y-2">
          {[1,2,3].map((i) => <Skeleton key={i} className="w-full" />)}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root App Component
// ---------------------------------------------------------------------------
export default function App() {
  const [view, setView] = useState<View>("home");
  const [repoOverview, setRepoOverview]   = useState<RepositoryOverview | null>(null);
  const [repoLoading, setRepoLoading]     = useState(false);
  const [repoError, setRepoError]         = useState<string | null>(null);

  const [issues, setIssues]           = useState<MatchedIssue[]>([]);
  const [issuesLoading, setIssuesLoading] = useState(false);
  const [issuesError, setIssuesError]     = useState<string | null>(null);

  const [plan, setPlan]           = useState<ContributionPlan | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError]     = useState<string | null>(null);

  const [health, setHealth]           = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  // Fetch health on mount
  React.useEffect(() => {
    api.health()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setHealthLoading(false));
  }, []);

  const handleAnalyze = useCallback(async (url: string) => {
    setRepoError(null);
    setRepoLoading(true);
    setView("overview");

    try {
      const result = await api.analyzeRepository(url);
      setRepoOverview(result.repository);
      // Reset downstream state
      setIssues([]);
      setPlan(null);
    } catch (err) {
      const msg = err instanceof APIError
        ? `${err.message}${err.detail ? ` — ${JSON.stringify(err.detail)}` : ""}`
        : "An unexpected error occurred. Is the backend running?";
      setRepoError(msg);
      setView("overview");
    } finally {
      setRepoLoading(false);
    }
  }, []);

  const handleGoIssues = useCallback(async () => {
    if (!repoOverview) return;
    setView("issues");

    if (issues.length > 0) return; // Already loaded

    setIssuesLoading(true);
    setIssuesError(null);
    try {
      const result = await api.matchIssues({
        owner: repoOverview.identity.owner,
        repo: repoOverview.identity.repo,
        skills: [],
        preferred_languages: repoOverview.primary_language ? [repoOverview.primary_language] : [],
        experience_level: "beginner",
        learning_preferences: [],
      });
      setIssues(result.matched_issues);
    } catch (err) {
      const msg = err instanceof APIError ? err.message : "Failed to load issues";
      setIssuesError(msg);
    } finally {
      setIssuesLoading(false);
    }
  }, [repoOverview, issues.length]);

  const handleSelectIssue = useCallback(async (matched: MatchedIssue) => {
    if (!repoOverview) return;
    setView("plan");
    setPlanLoading(true);
    setPlanError(null);

    try {
      const result = await api.generatePlan(
        repoOverview.identity.owner,
        repoOverview.identity.repo,
        matched.issue.number,
      );
      setPlan(result);
    } catch (err) {
      const msg = err instanceof APIError ? err.message : "Failed to generate plan";
      setPlanError(msg);
    } finally {
      setPlanLoading(false);
    }
  }, [repoOverview]);

  return (
    <div className="min-h-screen flex flex-col">
      <Nav
        view={view}
        setView={setView}
        hasRepo={!!repoOverview}
        health={health}
      />
      <div className="flex-1">
        {view === "home"     && <HomeView onAnalyze={handleAnalyze} />}
        {view === "overview" && <OverviewView repo={repoOverview} loading={repoLoading} error={repoError} onGoIssues={handleGoIssues} />}
        {view === "issues"   && <IssuesView issues={issues} loading={issuesLoading} error={issuesError} onSelectIssue={handleSelectIssue} owner={repoOverview?.identity.owner ?? ""} repo={repoOverview?.identity.repo ?? ""} />}
        {view === "plan"     && <PlanView plan={plan} repo={repoOverview} loading={planLoading} error={planError} />}
        {view === "settings" && <SettingsView health={health} healthLoading={healthLoading} />}
      </div>
      <footer className="border-t border-white/[0.04] py-4 text-center text-xs text-gray-700">
        FirstPatch AI · Evidence-backed open-source mentorship · v0.1.0
      </footer>
    </div>
  );
}
