"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { listRepositories, analyzeRepository } from "@/lib/api";
import {
  Compass,
  Search,
  Star,
  ArrowRight,
  Filter,
  Sparkles,
} from "lucide-react";

interface CuratedRepo {
  owner: string;
  repo: string;
  description: string;
  language: string;
  stars: number;
  tags: string[];
}

const CURATED_REPOSITORIES: CuratedRepo[] = [
  {
    owner: "tiangolo",
    repo: "fastapi",
    description: "FastAPI framework, high performance, easy to learn, fast to code, ready for production",
    language: "Python",
    stars: 76000,
    tags: ["web", "async", "api", "typing"],
  },
  {
    owner: "pallets",
    repo: "flask",
    description: "The Python micro framework for building web applications and APIs.",
    language: "Python",
    stars: 67000,
    tags: ["web", "framework", "wsgi", "jinja"],
  },
  {
    owner: "psf",
    repo: "requests",
    description: "A simple, yet elegant, HTTP library for Python, built for human beings.",
    language: "Python",
    stars: 52000,
    tags: ["http", "client", "network", "clean-code"],
  },
  {
    owner: "encode",
    repo: "httpx",
    description: "A next-generation HTTP client for Python with sync and async support.",
    language: "Python",
    stars: 13500,
    tags: ["async", "http2", "requests-compatible"],
  },
  {
    owner: "pydantic",
    repo: "pydantic",
    description: "Data validation and settings management using Python type hints.",
    language: "Python",
    stars: 21000,
    tags: ["validation", "schema", "core", "performance"],
  },
  {
    owner: "facebook",
    repo: "react",
    description: "The library for web and native user interfaces.",
    language: "JavaScript",
    stars: 228000,
    tags: ["ui", "components", "frontend"],
  },
  {
    owner: "vercel",
    repo: "next.js",
    description: "The React Framework for the Web with hybrid static & server rendering.",
    language: "TypeScript",
    stars: 125000,
    tags: ["react", "ssr", "fullstack"],
  },
  {
    owner: "expressjs",
    repo: "express",
    description: "Fast, unopinionated, minimalist web framework for Node.js.",
    language: "JavaScript",
    stars: 64000,
    tags: ["nodejs", "web", "middleware"],
  },
];

export default function ExplorePage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState<string>("All");
  const [indexedMap, setIndexedMap] = useState<Record<string, boolean>>({});
  const [analyzingRepo, setAnalyzingRepo] = useState<string | null>(null);

  useEffect(() => {
    listRepositories().then((repos) => {
      if (Array.isArray(repos)) {
        const map: Record<string, boolean> = {};
        repos.forEach((r) => { map[r.id] = true; });
        setIndexedMap(map);
      }
    });
  }, []);

  const handleAnalyze = async (owner: string, repo: string) => {
    const fullId = `${owner}/${repo}`;
    setAnalyzingRepo(fullId);
    try {
      await analyzeRepository(`https://github.com/${fullId}`);
      router.push(`/repo/${owner}/${repo}`);
    } catch {
      // Navigate to repo workspace directly
      router.push(`/repo/${owner}/${repo}`);
    } finally {
      setAnalyzingRepo(null);
    }
  };

  const languages = ["All", "Python", "TypeScript", "JavaScript"];

  const filtered = CURATED_REPOSITORIES.filter((r) => {
    const matchLang = selectedLanguage === "All" || r.language === selectedLanguage;
    const matchSearch =
      !search ||
      r.owner.toLowerCase().includes(search.toLowerCase()) ||
      r.repo.toLowerCase().includes(search.toLowerCase()) ||
      r.description.toLowerCase().includes(search.toLowerCase()) ||
      r.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()));
    return matchLang && matchSearch;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200/80 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-xl bg-purple-50 border border-purple-200/80 flex items-center justify-center text-purple-600 shadow-sm">
              <Compass className="w-4 h-4" />
            </span>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Explore Repositories</h1>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Discover curated beginner-friendly open-source codebases with active issue triage and clean AST structure.
          </p>
        </div>

        {/* Search */}
        <div className="relative max-w-xs w-full">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, topic..."
            className="input pl-10 py-2 text-xs"
          />
        </div>
      </div>

      {/* Language Filter Pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold text-gray-500 uppercase tracking-wider mr-2 flex items-center gap-1">
          <Filter className="w-3.5 h-3.5" /> Language:
        </span>
        {languages.map((lang) => (
          <button
            key={lang}
            onClick={() => setSelectedLanguage(lang)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
              selectedLanguage === lang
                ? "bg-brand-600 text-white shadow-md shadow-brand-500/25"
                : "bg-white text-gray-600 border border-gray-200/80 hover:border-brand-300"
            }`}
          >
            {lang}
          </button>
        ))}
      </div>

      {/* Repositories Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((r) => {
          const fullId = `${r.owner}/${r.repo}`;
          const isIndexed = !!indexedMap[fullId];
          const isAnalyzing = analyzingRepo === fullId;

          return (
            <div key={fullId} className="card-hover p-6 flex flex-col justify-between group">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="badge-brand font-mono text-[10px]">{r.language}</span>
                  <div className="flex items-center gap-2">
                    {isIndexed ? (
                      <span className="badge-success text-[10px]">Indexed</span>
                    ) : (
                      <span className="badge-muted text-[10px]">Ready to Ingest</span>
                    )}
                    <span className="flex items-center gap-1 text-xs text-amber-600 font-bold">
                      <Star className="w-3 h-3 fill-amber-400" /> {r.stars.toLocaleString()}
                    </span>
                  </div>
                </div>

                <h3 className="text-base font-bold text-gray-900 group-hover:text-brand-700 transition-colors">
                  {fullId}
                </h3>
                <p className="text-xs text-gray-500 line-clamp-3 mt-1.5 leading-relaxed">
                  {r.description}
                </p>

                <div className="flex flex-wrap gap-1.5 mt-3">
                  {r.tags.map((t) => (
                    <span key={t} className="badge-muted text-[10px] font-mono">
                      #{t}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-gray-100 flex items-center justify-between">
                {isIndexed ? (
                  <Link
                    href={`/repo/${r.owner}/${r.repo}`}
                    className="btn-secondary text-xs py-2 px-3.5 rounded-xl w-full justify-center text-brand-700 font-bold"
                  >
                    Open Workspace <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </Link>
                ) : (
                  <button
                    onClick={() => handleAnalyze(r.owner, r.repo)}
                    disabled={isAnalyzing}
                    className="btn-primary text-xs py-2 px-3.5 rounded-xl w-full justify-center font-bold"
                  >
                    {isAnalyzing ? (
                      <span className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                        Analyzing AST…
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5" />
                        Analyze &amp; Explore
                      </span>
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
