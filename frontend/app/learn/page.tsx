"use client";

import { useEffect, useState } from "react";
import { getBeginnerGlossary, getContributionSequence } from "@/lib/api";
import {
  BookOpen,
  Search,
  ShieldCheck,
} from "lucide-react";

export default function LearnPage() {
  const [glossary, setGlossary] = useState<any[]>([]);
  const [sequence, setSequence] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("All");

  useEffect(() => {
    getBeginnerGlossary().then((res) => {
      if (res?.glossary) setGlossary(res.glossary);
    });
    getContributionSequence().then((res) => {
      if (res?.sequence) setSequence(res.sequence);
    });
  }, []);

  const fallbackSequence = [
    {
      step: 1,
      name: "Problem Restatement",
      objective: "Articulate what fails in your own words before touching code.",
      why: "Ensures you truly understand the user issue rather than jumping to assumptions.",
    },
    {
      step: 2,
      name: "Expected vs Actual Delta",
      objective: "Pinpoint the exact behavioural discrepancy.",
      why: "Defines the success criterion for your future pull request.",
    },
    {
      step: 3,
      name: "Suspected Code Path",
      objective: "Locate specific file paths, classes, and function declarations.",
      why: "Grounds your hypothesis in verified AST symbols.",
    },
    {
      step: 4,
      name: "Minimal Reproduction",
      objective: "Isolate the smallest command or unit test that triggers the failure.",
      why: "Gives you a repeatable local test loop to prove your fix.",
    },
    {
      step: 5,
      name: "Hypothesis Ledger",
      objective: "Record your fix hypothesis along with supporting and contradicting evidence.",
      why: "Discloses uncertainty honestly instead of producing speculative patches.",
    },
    {
      step: 6,
      name: "Decision Gate",
      objective: "Decide whether to proceed, ask the maintainer for clarification, or choose another issue.",
      why: "Respects maintainer review bandwidth and prevents low-effort AI pull request spam.",
    },
  ];

  const stepsToDisplay = sequence.length > 0 ? sequence : fallbackSequence;

  const fallbackGlossary = [
    { term: "AST (Abstract Syntax Tree)", category: "Architecture", definition: "A tree representation of source code structure used to statically discover classes, functions, and imports without running untrusted code." },
    { term: "DCO / CLA", category: "Community", definition: "Developer Certificate of Origin or Contributor License Agreement certifying that you wrote or have the rights to submit the code." },
    { term: "Regression Test", category: "Verification", definition: "A unit test designed to reproduce an existing bug and guarantee it does not reoccur in future releases." },
    { term: "Blast Radius", category: "Architecture", definition: "The scope of potential downstream impacts or breakages across other modules caused by modifying a piece of code." },
    { term: "Flight Recorder", category: "Audit", definition: "An append-only ledger recording all test executions, verification outputs, and triage hypotheses for full transparency." },
    { term: "Reality Checker", category: "Audit", definition: "A truth matrix categorizing claims as statically VERIFIED, plausibly INFERRED, or explicitly UNKNOWN." },
  ];

  const termsToDisplay = glossary.length > 0 ? glossary : fallbackGlossary;

  const filteredGlossary = termsToDisplay.filter((item) => {
    const matchSearch =
      !search ||
      item.term.toLowerCase().includes(search.toLowerCase()) ||
      item.definition.toLowerCase().includes(search.toLowerCase());
    const matchCategory =
      activeCategory === "All" || item.category === activeCategory;
    return matchSearch && matchCategory;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10 animate-in">
      {/* Header */}
      <div className="border-b border-gray-200/80 pb-6">
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded-xl bg-purple-50 border border-purple-200/80 flex items-center justify-center text-purple-600 shadow-sm">
            <BookOpen className="w-4 h-4" />
          </span>
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Beginner Contributor Guide</h1>
        </div>
        <p className="text-xs sm:text-sm text-gray-500 mt-1 max-w-3xl">
          Everything you need to make your first open-source contribution with confidence, rigor, and maintainer etiquette.
        </p>
      </div>

      {/* 6-Step Contribution Pipeline Bento */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">The 6-Step Contribution Sequence</h2>
          <p className="text-xs text-gray-500">Triage thoroughly before generating any code</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {stepsToDisplay.map((s: any, idx: number) => (
            <div key={s.step || idx} className="card-hover p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="w-7 h-7 rounded-xl bg-brand-500 text-white font-extrabold text-xs flex items-center justify-center shadow-md">
                    {s.step || idx + 1}
                  </span>
                  <span className="badge-brand text-[10px] font-bold">PHASE {s.step || idx + 1}</span>
                </div>
                <h3 className="text-base font-bold text-gray-900 mb-1.5">{s.name || s.title}</h3>
                <p className="text-xs text-gray-600 leading-relaxed mb-3">
                  {s.objective || s.description}
                </p>
              </div>

              <div className="pt-3 border-t border-gray-100">
                <p className="text-[11px] text-gray-400 italic leading-snug">
                  <span className="font-bold text-gray-600 not-italic">Why it matters: </span>
                  {s.why || s.rationale}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Community Etiquette & Anti-Spam Standards */}
      <div className="card-brand p-6 sm:p-8 space-y-4">
        <div className="flex items-center gap-2 text-brand-700">
          <ShieldCheck className="w-5 h-5" />
          <h3 className="text-base font-bold text-gray-900">Open-Source Maintainer Etiquette</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-gray-600 leading-relaxed">
          <div className="space-y-2">
            <h4 className="font-bold text-gray-800 text-sm">Do:</h4>
            <ul className="space-y-1.5 list-disc pl-4 text-gray-600">
              <li>Always search existing issues and pull requests to ensure someone isn&apos;t already working on it.</li>
              <li>Ask politely if a fix is desired before spending hours writing code.</li>
              <li>Provide minimal, reproducible steps or failing unit tests in your discussion.</li>
              <li>Keep pull requests scoped strictly to one issue at a time.</li>
            </ul>
          </div>
          <div className="space-y-2">
            <h4 className="font-bold text-rose-700 text-sm">Don&apos;t:</h4>
            <ul className="space-y-1.5 list-disc pl-4 text-gray-600">
              <li>Do not submit raw, unverified AI chat output as pull request bodies.</li>
              <li>Do not modify unrelated formatting, docstrings, or lint configurations.</li>
              <li>Do not claim an issue without confirming you have a verified reproduction.</li>
              <li>Do not ping maintainers repeatedly; respect their volunteer time.</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Interactive Open-Source Glossary */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Open-Source Engineering Glossary</h2>
            <p className="text-xs text-gray-500">Key concepts every contributor should understand</p>
          </div>

          <div className="relative max-w-xs w-full">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search glossary terms…"
              className="input pl-10 py-2 text-xs"
            />
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="flex flex-wrap items-center gap-2">
          {["All", "Architecture", "Community", "Verification", "Audit"].map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                activeCategory === cat
                  ? "bg-brand-600 text-white shadow-sm"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-brand-300"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredGlossary.map((item) => (
            <div key={item.term} className="card p-5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-brand-700">{item.term}</span>
                {item.category && (
                  <span className="badge-muted text-[10px]">{item.category}</span>
                )}
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">
                {item.definition}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
