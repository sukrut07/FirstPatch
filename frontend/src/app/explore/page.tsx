"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeRepository } from "@/lib/api";
import { 
  Compass, 
  Search, 
  Star, 
  GitFork, 
  ArrowRight, 
  Layers, 
  Tag, 
  CheckCircle,
  ExternalLink
} from "lucide-react";

export default function ExplorePage() {
  const router = useRouter();
  const [selectedLang, setSelectedLang] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [analyzingRepo, setAnalyzingRepo] = useState<string | null>(null);

  const curatedRepos = [
    {
      owner: "pallets",
      name: "flask",
      language: "Python",
      description: "The Python micro framework for building web applications.",
      stars: 74900,
      forks: 17000,
      topics: ["python", "web", "microframework", "wsgi"],
      suitability: "High — clean AST structure and comprehensive unit test suite."
    },
    {
      owner: "tiangolo",
      name: "typer",
      language: "Python",
      description: "Typer, build great CLIs. Easy to code, based on Python type hints.",
      stars: 18200,
      forks: 900,
      topics: ["python", "cli", "type-hints"],
      suitability: "High — accessible codebase with well-documented issues."
    },
    {
      owner: "fastapi",
      name: "fastapi",
      language: "Python",
      description: "FastAPI framework, high performance, easy to learn, fast to code, ready for production.",
      stars: 82000,
      forks: 6900,
      topics: ["python", "api", "async", "pydantic"],
      suitability: "Medium — contains async loops and comprehensive validation fixtures."
    },
    {
      owner: "expressjs",
      name: "express",
      language: "JavaScript",
      description: "Fast, unopinionated, minimalist web framework for node.",
      stars: 65000,
      forks: 11000,
      topics: ["nodejs", "javascript", "web"],
      suitability: "High — classical router pattern and approachable unit tests."
    },
    {
      owner: "sukrut07",
      name: "HacktoberDYP",
      language: "Python",
      description: "Hacktoberfest DYP Open Source Contribution Workspace.",
      stars: 15,
      forks: 5,
      topics: ["hacktoberfest", "firstpatch"],
      suitability: "Direct — targeted workshop repository."
    }
  ];

  const languages = ["All", "Python", "JavaScript"];

  const filtered = curatedRepos.filter((r) => {
    const matchesLang = selectedLang === "All" || r.language === selectedLang;
    const matchesQuery = !searchQuery || 
      `${r.owner}/${r.name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLang && matchesQuery;
  });

  const handleSelect = async (owner: string, name: string) => {
    const fullName = `${owner}/${name}`;
    setAnalyzingRepo(fullName);
    try {
      await analyzeRepository(fullName);
      router.push(`/repo/${owner}/${name}`);
    } catch {
      // Direct navigation if already indexed
      router.push(`/repo/${owner}/${name}`);
    } finally {
      setAnalyzingRepo(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-medium mb-3">
          <Compass className="h-3 w-3" />
          <span>Curated Open-Source Directory</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Explore Open-Source Repositories</h1>
        <p className="text-xs text-zinc-400 mt-1 max-w-2xl">
          Choose from verified repositories structured for first-time contributors. FirstPatch will parse the codebase, extract functions and test suites, and match approachable issues.
        </p>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        {/* Language Tabs */}
        <div className="flex items-center gap-1.5 bg-zinc-900 p-1 rounded-lg border border-zinc-800">
          {languages.map((lang) => (
            <button
              key={lang}
              onClick={() => setSelectedLang(lang)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                selectedLang === lang
                  ? "bg-zinc-800 text-zinc-100 border border-zinc-700 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {lang}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
          <input
            type="text"
            placeholder="Filter by name or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Repo Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((repo) => {
          const fullName = `${repo.owner}/${repo.name}`;
          const isAnalyzing = analyzingRepo === fullName;
          return (
            <div
              key={fullName}
              className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="font-bold text-sm text-zinc-100 flex items-center gap-1.5">
                    {fullName}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-400 border border-zinc-700/50">
                    {repo.language}
                  </span>
                </div>

                <p className="text-xs text-zinc-400 mb-3 line-clamp-2 leading-relaxed">
                  {repo.description}
                </p>

                {/* Suitability note */}
                <div className="p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 text-[11px] text-zinc-400 mb-4">
                  <span className="text-emerald-400 font-semibold block mb-0.5">Contributor Fit:</span>
                  {repo.suitability}
                </div>

                {/* Topics */}
                <div className="flex flex-wrap gap-1 mb-4">
                  {repo.topics.map((t) => (
                    <span key={t} className="px-1.5 py-0.5 rounded bg-zinc-800/60 text-[10px] font-mono text-zinc-500">
                      #{t}
                    </span>
                  ))}
                </div>
              </div>

              {/* Bottom Actions */}
              <div className="border-t border-zinc-800/80 pt-3 flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-zinc-400">
                  <span className="flex items-center gap-1">
                    <Star className="h-3 w-3 text-amber-400" />
                    {repo.stars.toLocaleString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <GitFork className="h-3 w-3" />
                    {repo.forks.toLocaleString()}
                  </span>
                </div>

                <button
                  onClick={() => handleSelect(repo.owner, repo.name)}
                  disabled={isAnalyzing}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-xs font-semibold transition-all disabled:opacity-50 cursor-pointer"
                >
                  {isAnalyzing ? (
                    <>
                      <span className="h-3 w-3 border-2 border-zinc-950 border-t-transparent rounded-full animate-spin"></span>
                      Indexing...
                    </>
                  ) : (
                    <>
                      Analyze & Mentor
                      <ArrowRight className="h-3 w-3" />
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
