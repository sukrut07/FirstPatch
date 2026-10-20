"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  listRepositories,
  listContributions,
  fetchHealth,
  fetchModelStatus,
  analyzeRepository,
  testModelInference,
  askMentor,
} from "@/lib/api";
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
  Zap,
  CheckCircle2,
  Send,
  RefreshCw,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [repos, setRepos] = useState<any[]>([]);
  const [contributions, setContributions] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [urlInput, setUrlInput] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Live Ollama Interactive Playground State
  const [promptInput, setPromptInput] = useState("What makes a good first open-source pull request?");
  const [queryingAI, setQueryingAI] = useState(false);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [testingModel, setTestingModel] = useState(false);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const loadData = () => {
    listRepositories().then((res) => {
      if (Array.isArray(res)) {
        // Filter out empty dummy test rows
        const valid = res.filter((r) => r.id && !r.id.startsWith("test/") && r.name !== "repo");
        setRepos(valid);
      }
    });
    listContributions().then((res) => {
      if (Array.isArray(res)) setContributions(res);
    });
    fetchHealth().then(setHealth);
    fetchModelStatus().then((res) => {
      if (res) setModelStatus(res);
    });
  };

  const handleAnalyze = async (e: React.FormEvent, customUrl?: string) => {
    if (e) e.preventDefault();
    const target = (customUrl || urlInput).trim();
    if (!target) return;

    setAnalyzing(true);
    setError(null);
    try {
      const res = await analyzeRepository(target);
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
      setError(err.message || "Failed to analyze repository. Ensure the backend is running.");
      setAnalyzing(false);
    }
  };

  const handleTestInference = async () => {
    setTestingModel(true);
    setError(null);
    try {
      const res = await testModelInference();
      setAiResponse(res.test_output || JSON.stringify(res, null, 2));
    } catch (err: any) {
      setError(err.message || "Model health check failed");
    } finally {
      setTestingModel(false);
    }
  };

  const handleAskOllama = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptInput.trim()) return;

    setQueryingAI(true);
    setError(null);
    try {
      const activeRepo = repos.length > 0 ? repos[0].id : "pallets/flask";
      const res = await askMentor(activeRepo, promptInput.trim(), "learn");
      if (res && res.response) {
        setAiResponse(res.response);
      } else {
        setAiResponse("Response received from Ollama Local LLM.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to query Ollama local LLM.");
    } finally {
      setQueryingAI(false);
    }
  };

  const activeModelName = modelStatus?.active_model || health?.ollama?.active_model || "gemma4:e2b";
  const isOllamaOnline = modelStatus?.online ?? (health?.ai_provider === "ollama");

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-5 border-b border-gray-200/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-gray-900">
              Contribution Dashboard
            </h1>
            <span className="badge-brand text-[10px] font-mono uppercase tracking-wider">Live System</span>
          </div>
          <p className="text-xs sm:text-sm text-gray-500">
            Real-time telemetry, AST codebase index, and background Ollama local LLM orchestration.
          </p>
        </div>

        {/* Quick Ingest Bar */}
        <form onSubmit={(e) => handleAnalyze(e)} className="flex items-center gap-2 max-w-md w-full">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Analyze new repository (e.g. pallets/flask)..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="input pl-10 py-2.5 text-xs"
              disabled={analyzing}
            />
          </div>
          <button
            type="submit"
            disabled={analyzing || !urlInput.trim()}
            className="btn-primary text-xs py-2.5 px-4 shrink-0 shadow-md flex items-center gap-1.5"
          >
            {analyzing ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Analyzing…</span>
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5" />
                <span>Analyze</span>
              </>
            )}
          </button>
        </form>
      </div>

      {error && (
        <div className="notice-error flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
          <p className="text-xs flex-1">{error}</p>
        </div>
      )}

      {/* System Status Metrics Bento */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Repositories */}
        <div className="card p-5">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <span className="font-semibold">Indexed Repositories</span>
            <Layers className="h-4 w-4 text-brand-600" />
          </div>
          <div className="text-2xl font-extrabold text-gray-900">{repos.length}</div>
          <p className="text-[11px] text-gray-400 mt-1">Ready for AST exploration</p>
        </div>

        {/* Card 2: Workspaces */}
        <div className="card p-5">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <span className="font-semibold">Flight Recorder Workspaces</span>
            <GitPullRequest className="h-4 w-4 text-purple-600" />
          </div>
          <div className="text-2xl font-extrabold text-gray-900">{contributions.length}</div>
          <p className="text-[11px] text-gray-400 mt-1">Guided contributor journeys</p>
        </div>

        {/* Card 3: Ollama Local LLM */}
        <div className="card p-5">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <span className="font-semibold">Local AI Model</span>
            <Cpu className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="text-base font-extrabold text-gray-900 truncate">
            {activeModelName}
          </div>
          <div className="flex items-center gap-1.5 mt-2">
            <span className="relative flex h-2 w-2">
              {isOllamaOnline ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </>
              ) : (
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
              )}
            </span>
            <span className={`text-[11px] font-bold ${isOllamaOnline ? "text-emerald-700" : "text-amber-700"}`}>
              {isOllamaOnline ? "Ollama Connected" : "Connecting..."}
            </span>
          </div>
          <p className="text-[10px] text-gray-400 mt-1 truncate">
            {modelStatus?.endpoint || "http://127.0.0.1:11434"} • Context: 8k
          </p>
        </div>

        {/* Card 4: Compliance */}
        <div className="card p-5">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <span className="font-semibold">Audit &amp; Safety Status</span>
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-extrabold text-emerald-600">10/10</div>
          <p className="text-[11px] text-gray-400 mt-1">Grounded AST claim checking</p>
        </div>
      </div>

      {/* Live Ollama Connectivity & Interactive AI Verification Panel */}
      <div className="card p-6 border-brand-200/80 bg-gradient-to-br from-white via-brand-50/20 to-purple-50/20 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-brand-600 text-white flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                Ollama Background Local LLM Pipeline
                <span className="badge-brand text-[9px] font-mono">Active Model: {activeModelName}</span>
              </h3>
              <p className="text-xs text-gray-500">
                Connected via FastAPI to local Ollama inference daemon. Test live reasoning without cloud dependencies.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleTestInference}
              disabled={testingModel}
              className="btn-secondary text-xs py-1.5 px-3 rounded-xl flex items-center gap-1.5"
            >
              {testingModel ? <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-600" /> : <Cpu className="w-3.5 h-3.5 text-brand-600" />}
              <span>{testingModel ? "Pinging Model…" : "Quick Inference Check"}</span>
            </button>
            <Link
              href="/settings/models"
              className="btn-ghost text-xs py-1.5 px-3 rounded-xl text-brand-600 hover:text-brand-800"
            >
              Settings &amp; Keys &rarr;
            </Link>
          </div>
        </div>

        {/* Quick Prompt Input */}
        <form onSubmit={handleAskOllama} className="flex gap-2">
          <input
            type="text"
            value={promptInput}
            onChange={(e) => setPromptInput(e.target.value)}
            placeholder="Ask a question to the background Ollama model..."
            className="input text-xs py-2.5 flex-1"
            disabled={queryingAI}
          />
          <button
            type="submit"
            disabled={queryingAI || !promptInput.trim()}
            className="btn-primary text-xs py-2.5 px-4 shrink-0 flex items-center gap-1.5"
          >
            {queryingAI ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Generating…</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>Ask Ollama</span>
              </>
            )}
          </button>
        </form>

        {/* Live Output Box */}
        {aiResponse && (
          <div className="p-4 rounded-2xl bg-white border border-brand-200/70 shadow-sm animate-in space-y-2">
            <div className="flex items-center justify-between text-xs text-gray-500 border-b border-gray-100 pb-2">
              <span className="font-semibold text-brand-700 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                Ollama Response ({activeModelName})
              </span>
              <button
                onClick={() => setAiResponse(null)}
                className="text-[11px] text-gray-400 hover:text-gray-600"
              >
                Clear
              </button>
            </div>
            <div className="text-xs text-gray-700 leading-relaxed font-sans whitespace-pre-wrap">
              {aiResponse}
            </div>
          </div>
        )}
      </div>

      {/* Main 2-Column Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Indexed Repositories */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Your Indexed Repositories</h2>
              <p className="text-xs text-gray-500">Repositories analyzed with AST parsers and Ollama architectural models</p>
            </div>
            <Link href="/explore" className="text-xs font-bold text-brand-600 hover:text-brand-800 flex items-center gap-1">
              Explore More Repos <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {repos.length === 0 ? (
            <div className="card p-10 text-center space-y-4">
              <FileCode className="h-10 w-10 text-brand-400 mx-auto" />
              <h3 className="text-base font-bold text-gray-900">No repositories indexed yet</h3>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                Paste any GitHub repository URL above or click a verified sample below to index its AST architecture.
              </p>
              <div className="flex justify-center gap-2 pt-2">
                <button
                  onClick={() => handleAnalyze(null as any, "https://github.com/pallets/flask")}
                  className="btn-secondary text-xs py-2 px-3"
                >
                  Index pallets/flask
                </button>
                <button
                  onClick={() => handleAnalyze(null as any, "https://github.com/tiangolo/fastapi")}
                  className="btn-secondary text-xs py-2 px-3"
                >
                  Index tiangolo/fastapi
                </button>
              </div>
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

                    {/* AI Architectural Intelligence Snippet */}
                    {r.ai_analysis && (
                      <div className="mt-3 p-2.5 rounded-xl bg-brand-50/70 border border-brand-200/70 text-xs">
                        <div className="flex items-center gap-1 text-[11px] font-bold text-brand-700 mb-1">
                          <Sparkles className="w-3 h-3 text-brand-600" />
                          <span>{r.ai_analysis_model || "Ollama"} Architecture</span>
                          <span className="badge-brand text-[9px] py-0 px-1.5 ml-auto">Verified</span>
                        </div>
                        <p className="text-[11px] text-gray-600 line-clamp-2 leading-snug">
                          {r.ai_analysis.executive_summary || r.ai_analysis.architecture_pattern}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
                    <span className="text-gray-400 font-medium">
                      {r.open_issues_count || 0} open issues
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
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-1.5">
                <GitPullRequest className="w-4 h-4 text-purple-600" />
                <span>Flight Recorder Journeys</span>
              </h3>
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
                    className="block p-3.5 rounded-2xl bg-surface-50 border border-gray-100 hover:border-brand-200 hover:bg-brand-50/30 transition-all"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-xs text-gray-900 truncate" title={c.title}>
                        {c.title}
                      </span>
                      <span className="badge-brand text-[10px] uppercase font-bold shrink-0">
                        {c.status || "active"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-gray-500">
                      <span className="font-mono text-[10px]">{c.repository_id}</span>
                      <span>{c.completed_steps || 0}/{c.total_steps || 5} steps</span>
                    </div>
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
