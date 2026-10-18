"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getBeginnerGlossary, getContributionSequence } from "@/lib/api";
import { 
  BookOpen, 
  Search, 
  Compass, 
  GitFork, 
  GitBranch, 
  CheckCircle2, 
  Terminal, 
  ArrowRight, 
  Sparkles, 
  ShieldCheck, 
  FileText, 
  HelpCircle, 
  Layers,
  ChevronDown,
  ChevronRight
} from "lucide-react";

export default function BeginnerLearningPage() {
  const [glossary, setGlossary] = useState<any[]>([]);
  const [sequence, setSequence] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [expandedStep, setExpandedStep] = useState<number | null>(1);
  const [userLevel, setUserLevel] = useState<"beginner" | "intermediate" | "advanced">("beginner");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getBeginnerGlossary(), getContributionSequence()]).then(([gRes, sRes]) => {
      if (gRes?.glossary) setGlossary(gRes.glossary);
      if (sRes?.sequence) setSequence(sRes.sequence);
      setLoading(false);
    });
  }, []);

  const categories = ["All", "Git & GitHub", "Testing & CI", "Code & Architecture", "Compliance"];

  const filteredGlossary = glossary.filter((item) => {
    const matchesSearch = item.term.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          item.definition.toLowerCase().includes(searchQuery.toLowerCase());
    if (selectedCategory === "All") return matchesSearch;
    return matchesSearch && (item.category === selectedCategory || !item.category);
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-medium mb-3">
          <BookOpen className="h-3.5 w-3.5" />
          <span>Beginner Onboarding & Knowledge Center</span>
        </div>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-zinc-100">
              Your Guide to First-Time Open-Source Contribution
            </h1>
            <p className="text-sm text-zinc-400 mt-1 max-w-3xl">
              Understand how open-source repositories work, master the terminology, and follow the verifiable 18-step contribution sequence from orientation to merged pull request.
            </p>
          </div>

          {/* Explanation Level Selector */}
          <div className="flex items-center gap-1 p-1 bg-zinc-900 border border-zinc-800 rounded-lg text-xs self-start md:self-auto">
            {(["beginner", "intermediate", "advanced"] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setUserLevel(lvl)}
                className={`px-3 py-1.5 rounded-md capitalize font-medium transition-colors cursor-pointer ${
                  userLevel === lvl 
                    ? "bg-emerald-500 text-zinc-950 font-semibold" 
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Section 1: The 18-Step Contribution Sequence */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-zinc-800 pb-4">
          <div>
            <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
              <Compass className="h-5 w-5 text-emerald-400" />
              The 18-Step Open-Source Contribution Lifecycle
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Click any milestone to view prerequisites, common pitfalls, and expected verification results.
            </p>
          </div>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20 shrink-0">
            18 Interactive Steps
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12 gap-3 text-xs text-zinc-400">
            <span className="h-5 w-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></span>
            Loading contribution lifecycle...
          </div>
        ) : (
          <div className="space-y-3">
            {sequence.map((step: any) => {
              const isExpanded = expandedStep === step.step;
              return (
                <div
                  key={step.step}
                  className={`rounded-lg border transition-all ${
                    isExpanded 
                      ? "border-emerald-500/50 bg-zinc-900/90 shadow-lg shadow-emerald-500/5" 
                      : "border-zinc-800/80 bg-zinc-950/60 hover:border-zinc-700"
                  }`}
                >
                  <button
                    onClick={() => setExpandedStep(isExpanded ? null : step.step)}
                    className="w-full flex items-center justify-between p-3.5 text-left cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <span className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-mono font-bold ${
                        isExpanded ? "bg-emerald-500 text-zinc-950" : "bg-zinc-800 text-zinc-400 border border-zinc-700"
                      }`}>
                        {step.step}
                      </span>
                      <div>
                        <div className="text-xs font-semibold text-zinc-200 flex items-center gap-2">
                          {step.title}
                          {step.phase && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                              {step.phase}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-zinc-400 line-clamp-1">{step.description}</p>
                      </div>
                    </div>
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-emerald-400 shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-zinc-500 shrink-0" />
                    )}
                  </button>

                  {isExpanded && (
                    <div className="px-4 pb-4 pt-1 border-t border-zinc-800/80 space-y-3 text-xs">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                        <div className="bg-zinc-950 p-3 rounded border border-zinc-800/80">
                          <strong className="text-emerald-400 block mb-1 font-mono uppercase text-[10px]">
                            Why This Matters
                          </strong>
                          <p className="text-zinc-300 text-[11px] leading-relaxed">
                            {step.why || step.description}
                          </p>
                        </div>
                        <div className="bg-zinc-950 p-3 rounded border border-zinc-800/80">
                          <strong className="text-cyan-400 block mb-1 font-mono uppercase text-[10px]">
                            Expected Verification Result
                          </strong>
                          <p className="text-zinc-300 text-[11px] leading-relaxed">
                            {step.verification || "Confirmed locally with clean git status and zero test regressions."}
                          </p>
                        </div>
                      </div>

                      {step.command && (
                        <div className="bg-zinc-950 p-2.5 rounded border border-zinc-800 font-mono text-[11px] text-emerald-400 flex items-center justify-between">
                          <span>$ {step.command}</span>
                          <span className="text-[10px] text-zinc-500">Terminal Command</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Section 2: Interactive Beginner Glossary */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
          <div>
            <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
              <FileText className="h-5 w-5 text-cyan-400" />
              Open-Source Beginner Glossary ({filteredGlossary.length} terms)
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Clear, practical definitions with repository context—no academic jargon.
            </p>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-72">
            <Search className="h-4 w-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search glossary..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        {/* Glossary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredGlossary.map((item) => (
            <div
              key={item.term}
              className="rounded-lg border border-zinc-800/80 bg-zinc-950/70 p-4 hover:border-zinc-700 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-bold font-mono text-emerald-400">{item.term}</h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                    {item.category || "General"}
                  </span>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed mb-3">
                  {item.definition}
                </p>
              </div>
              {item.example && (
                <div className="pt-2 border-t border-zinc-800/80 text-[11px] font-mono text-zinc-500 bg-zinc-900/40 p-2 rounded">
                  <span className="text-zinc-400 font-semibold">Example: </span>{item.example}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
