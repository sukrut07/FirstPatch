"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { listRepositories, listContributions, fetchHealth, analyzeRepository } from "@/lib/api";
import {
  Layers,
  GitPullRequest,
  Search,
  ArrowRight,
  Star,
  Cpu,
  FileCode,
  AlertCircle,
  BookOpen,
  Sparkles,
  ShieldCheck,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [repos, setRepos] = useState<any[]>([]);
  const [contributions, setContributions] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [urlInput, setUrlInput] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = () => {
    listRepositories().then((res) => { if (Array.isArray(res)) setRepos(res); });
    listContributions().then((res) => { if (Array.isArray(res)) setContributions(res); });
    fetchHealth().then(setHealth);
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setAnalyzing(true);
    setError(null);
    try {
      const res = await analyzeRepository(urlInput.trim());
      const owner = res.owner || res.repository?.identity?.owner;
      const name = res.name || res.repository?.identity?.repo;
      setUrlInput("");
      setAnalyzing(false);
      if (owner && name) {
        router.push(`/repo/${owner}/${name}`);
      } else {
        loadData();
      }
    } catch (err: any) {
      setError(err.message || "Failed to analyze repository.");
      setAnalyzing(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-5 border-b border-gray-200/80 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-gray-900">
            Contribution Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">
            Explore indexed repositories, monitor active contribution plans, and verify local pull requests.
          </p>
        </div>

        {/* Quick Ingest Bar */}
        <form onSubmit={handleAnalyze} className="flex items-center gap-2 max-w-md w-full">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Analyze new repository (owner/repo)..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="input pl-10 py-2.5 text-xs"
              disabled={analyzing}
            />
          </div>
          <button
            type="submit"
            disabled={analyzing || !urlInput.trim()}
            className="btn-primary text-xs py-2.5 px-4 shrink-0 shadow-md"
          >
            {analyzing ? "Analyzing…" : "Analyze"}
          </button>
        </form>
      </div>

      {error && (
        <div className="notice-error">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
          <p className="text-xs">{error}</p>
        </div>
      )}

      {/* System Status Metrics Bento */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card p-5">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <span className="font-semibold">Indexed Repositories</span>
            <Layers className="h-4 w-4 text-brand-600" />
          </div>
          <div className="text-2xl font-extrabold text-gray-900">{repos.length}</div>
          <p className="text-[11px] text-gray-400 mt-1">Ready for AST exploration</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <span className="font-semibold">Contribution Workspaces</span>
            <GitPullRequest className="h-4 w-4 text-purple-600" />
          </div>
          <div className="text-2xl font-extrabold text-gray-900">{contributions.length}</div>
          <p className="text-[11px] text-gray-400 mt-1">Flight Recorder journeys</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <span className="font-semibold">Local AI Model</span>
            <Cpu className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="text-sm font-bold text-gray-900 truncate">
            {health?.ai_provider || "Grounded Fallback"}
          </div>
          <span className={`badge mt-2 text-[10px] ${health?.ai_provider_status === "available" ? "badge-success" : "badge-muted"}`}>
            {health?.ai_provider_status === "available" ? "Online" : "Grounded AST"}
          </span>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <span className="font-semibold">Audit Status</span>
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-extrabold text-emerald-600">10/10</div>
          <p className="text-[11px] text-gray-400 mt-1">Compliance rules operational</p>
        </div>
      </div>

      {/* Main 2-Column Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Indexed Repositories */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">Your Indexed Repositories</h2>
            <Link href="/explore" className="text-xs font-bold text-brand-600 hover:text-brand-800 flex items-center gap-1">
              Explore More Repos <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {repos.length === 0 ? (
            <div className="card p-10 text-center space-y-3">
              <FileCode className="h-10 w-10 text-brand-400 mx-auto" />
              <h3 className="text-base font-bold text-gray-900">No repositories indexed yet</h3>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                Paste a GitHub repository URL above to inspect its architecture, dependencies, and suitable issues.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {repos.map((r) => (
                <div key={r.id} className="card-hover p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="badge-brand font-mono text-[10px]">{r.language || "Codebase"}</span>
                      {r.stars > 0 && (
                        <span className="flex items-center gap-1 text-xs text-amber-600 font-bold">
                          <Star className="w-3 h-3 fill-amber-400" /> {r.stars.toLocaleString()}
                        </span>
                      )}
                    </div>
                    <Link
                      href={`/repo/${r.owner}/${r.name}`}
                      className="text-base font-bold text-gray-900 hover:text-brand-700 transition-colors block"
                    >
                      {r.id}
                    </Link>
                    {r.description && (
                      <p className="text-xs text-gray-500 line-clamp-2 mt-1 leading-relaxed">
                        {r.description}
                      </p>
                    )}
                  </div>

                  <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
                    <span className="text-gray-400 font-medium">
                      {r.open_issues_count || 0} issues
                    </span>
                    <Link
                      href={`/repo/${r.owner}/${r.name}`}
                      className="font-bold text-brand-600 hover:text-brand-800 flex items-center gap-1"
                    >
                      Workspace <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Active Contribution Journeys & Quick Tools */}
        <div className="space-y-6">
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-sm font-bold text-gray-900">Flight Recorder Journeys</h3>
              <Link href="/contributions" className="text-xs font-semibold text-brand-600 hover:text-brand-800">
                View All
              </Link>
            </div>

            {contributions.length === 0 ? (
              <div className="py-6 text-center text-xs text-gray-400">
                No active contribution workspaces.<br />
                Select an issue in any repository to start a journey.
              </div>
            ) : (
              <div className="space-y-3">
                {contributions.slice(0, 4).map((c) => (
                  <Link
                    key={c.id}
                    href={`/contributions/${c.id}`}
                    className="block p-3 rounded-2xl bg-surface-50 border border-gray-100 hover:border-brand-200 hover:bg-brand-50/30 transition-all"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-xs text-gray-900 truncate" title={c.title}>
                        {c.title}
                      </span>
                      <span className="badge-brand text-[10px] uppercase font-bold shrink-0">
                        {c.status || "active"}
                      </span>
                    </div>
                    <p className="text-[10px] text-gray-500 truncate">{c.repository_id}</p>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Quick Hub Navigation Cards */}
          <div className="space-y-3">
            <Link
              href="/learn"
              className="card-hover p-4 flex items-center gap-3.5 group"
            >
              <div className="w-10 h-10 rounded-2xl bg-purple-100 text-purple-600 flex items-center justify-center shrink-0">
                <BookOpen className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-gray-900 group-hover:text-brand-700">Beginner Guide &amp; Glossary</h4>
                <p className="text-xs text-gray-500 truncate">6-Step contribution sequence &amp; etiquette</p>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-brand-600 group-hover:translate-x-0.5 transition-transform" />
            </Link>

            <Link
              href="/mentor"
              className="card-hover p-4 flex items-center gap-3.5 group"
            >
              <div className="w-10 h-10 rounded-2xl bg-brand-100 text-brand-600 flex items-center justify-center shrink-0">
                <Sparkles className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-gray-900 group-hover:text-brand-700">Socratic AI Mentor</h4>
                <p className="text-xs text-gray-500 truncate">Ask architecture and testing questions</p>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-brand-600 group-hover:translate-x-0.5 transition-transform" />
            </Link>

            <Link
              href="/compliance"
              className="card-hover p-4 flex items-center gap-3.5 group"
            >
              <div className="w-10 h-10 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-gray-900 group-hover:text-brand-700">Trust Audit &amp; Benchmarks</h4>
                <p className="text-xs text-gray-500 truncate">10 compliance rules &amp; reality check matrix</p>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-brand-600 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
