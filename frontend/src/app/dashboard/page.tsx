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
  GitFork, 
  CheckCircle2, 
  Clock, 
  Cpu, 
  FileCode, 
  AlertCircle,
  Plus
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
    listRepositories().then(setRepos);
    listContributions().then(setContributions);
    fetchHealth().then(setHealth);
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setAnalyzing(true);
    setError(null);
    try {
      const res = await analyzeRepository(urlInput.trim());
      setUrlInput("");
      setAnalyzing(false);
      router.push(`/repo/${res.owner}/${res.name}`);
    } catch (err: any) {
      setError(err.message || "Failed to analyze repository.");
      setAnalyzing(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Contribution Dashboard</h1>
          <p className="text-xs text-zinc-400 mt-1">
            Explore indexed repositories, monitor active contribution plans, and verify local pull requests.
          </p>
        </div>

        {/* Quick Ingest Bar */}
        <form onSubmit={handleAnalyze} className="flex items-center gap-2 max-w-md w-full">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
            <input
              type="text"
              placeholder="Analyze new repository..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
              disabled={analyzing}
            />
          </div>
          <button
            type="submit"
            disabled={analyzing || !urlInput.trim()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors shrink-0 disabled:opacity-50 cursor-pointer"
          >
            {analyzing ? "Analyzing..." : "Analyze"}
          </button>
        </form>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400">
          {error}
        </div>
      )}

      {/* System Status Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="flex items-center justify-between text-xs text-zinc-400 mb-2">
            <span>Indexed Repositories</span>
            <Layers className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-zinc-100">{repos.length}</div>
          <p className="text-[11px] text-zinc-500 mt-1">Ready for AST exploration</p>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="flex items-center justify-between text-xs text-zinc-400 mb-2">
            <span>Contribution Workspaces</span>
            <GitPullRequest className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-zinc-100">{contributions.length}</div>
          <p className="text-[11px] text-zinc-500 mt-1">Flight Recorder journeys</p>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="flex items-center justify-between text-xs text-zinc-400 mb-2">
            <span>Local AI Model</span>
            <Cpu className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-sm font-bold font-mono text-zinc-100 truncate">
            {health?.ollama?.online ? health.ollama.active_model : "Offline"}
          </div>
          <p className="text-[11px] text-zinc-500 mt-1">
            {health?.ollama?.online ? "Ollama service connected" : "Start ollama serve locally"}
          </p>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="flex items-center justify-between text-xs text-zinc-400 mb-2">
            <span>Grounding Ledger</span>
            <CheckCircle2 className="h-4 w-4 text-teal-400" />
          </div>
          <div className="text-sm font-semibold text-zinc-100">FTS5 + AST Verified</div>
          <p className="text-[11px] text-zinc-500 mt-1">Zero code hallucination</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Analyzed Repositories (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Analyzed Repositories</h2>
            <Link href="/explore" className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1">
              Explore more repos <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {repos.length === 0 ? (
            <div className="rounded-xl border border-dashed border-zinc-800 p-8 text-center bg-zinc-900/20">
              <Layers className="h-8 w-8 text-zinc-600 mx-auto mb-3" />
              <p className="text-sm font-medium text-zinc-300">No repositories analyzed yet.</p>
              <p className="text-xs text-zinc-500 mt-1 mb-4">Paste any public GitHub repository link above to get started.</p>
              <Link
                href="/explore"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200 border border-zinc-700 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
                Browse Suggested Repositories
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {repos.map((repo) => (
                <Link
                  key={repo.id}
                  href={`/repo/${repo.owner}/${repo.name}`}
                  className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all flex flex-col justify-between group"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span className="font-semibold text-sm text-zinc-200 group-hover:text-emerald-400 transition-colors truncate">
                        {repo.owner}/{repo.name}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-400 border border-zinc-700/50">
                        {repo.language || "Python"}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-400 line-clamp-2 mb-3 leading-relaxed">
                      {repo.description || "No description provided."}
                    </p>
                  </div>

                  <div className="flex items-center justify-between text-xs text-zinc-500 border-t border-zinc-800/60 pt-3">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3 text-amber-400" />
                        {repo.stars?.toLocaleString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <GitFork className="h-3 w-3" />
                        {repo.forks?.toLocaleString()}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
                      Explore <ArrowRight className="h-3 w-3" />
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Active Contribution Workspaces (1 col) */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Flight Recorder Journeys</h2>
            <Link href="/contributions" className="text-xs text-zinc-400 hover:text-zinc-300">
              View all
            </Link>
          </div>

          {contributions.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-6 text-center text-xs text-zinc-500">
              <GitPullRequest className="h-6 w-6 text-zinc-600 mx-auto mb-2" />
              <p className="font-medium text-zinc-400">No active workspaces.</p>
              <p className="mt-1">Pick an issue from any analyzed repository to generate a contribution plan.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {contributions.slice(0, 5).map((c) => {
                const progressPct = c.total_steps > 0 ? Math.round((c.completed_steps / c.total_steps) * 100) : 0;
                return (
                  <Link
                    key={c.id}
                    href={`/contributions/${c.id}`}
                    className="block rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 hover:border-zinc-700 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <span className="text-xs font-semibold text-zinc-200 line-clamp-1">{c.title}</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {c.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 font-mono mb-3">{c.repository_id}</p>

                    {/* Progress Bar */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[10px] text-zinc-400">
                        <span>Steps: {c.completed_steps}/{c.total_steps}</span>
                        <span>{progressPct}%</span>
                      </div>
                      <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-emerald-500 h-full rounded-full transition-all duration-300"
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
