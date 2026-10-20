"use client";

import React, { useState, useMemo } from "react";
import {
  Layers,
  Network,
  GitBranch,
  FileCode,
  CheckCircle2,
  Folder,
  ArrowRight,
  Info,
  Terminal,
  BarChart3,
  Copy,
  Check,
  Search,
  Code2,
} from "lucide-react";

interface CodebaseDiagramsProps {
  files?: any[];
  arch?: any;
  issues?: any[];
  repoData?: any;
}

export default function CodebaseDiagrams({
  files = [],
  arch,
  issues = [],
  repoData,
}: CodebaseDiagramsProps) {
  const [activeTab, setActiveTab] = useState<"architecture" | "dependencies" | "workflow" | "mermaid" | "composition">("architecture");
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [depSearch, setDepSearch] = useState("");
  const [copiedMermaid, setCopiedMermaid] = useState(false);

  // 1. Architecture layers derived strictly from REAL analysis data
  const architectureLayers = useMemo(() => {
    if (!arch && (!files || files.length === 0)) return null;

    const entrypoints: any[] = [];
    const coreModules: any[] = [];
    const testFiles: any[] = [];
    const configFiles: any[] = [];

    const modules = arch?.modules || [];

    if (modules.length > 0) {
      modules.forEach((m: any) => {
        if (m.is_entrypoint) entrypoints.push(m);
        else if (m.is_test) testFiles.push(m);
        else coreModules.push(m);
      });
    } else {
      // Fallback from raw files
      files.forEach((f: any) => {
        if (f.is_entrypoint) entrypoints.push(f);
        else if (f.is_test) testFiles.push(f);
        else if (f.is_config) configFiles.push(f);
        else coreModules.push(f);
      });
    }

    // Default entrypoint if arch exists but entrypoints array is empty
    if (entrypoints.length === 0 && arch?.entrypoints && arch.entrypoints.length > 0) {
      arch.entrypoints.forEach((ep: string) => {
        entrypoints.push({ path: ep, functions: [], classes: [], is_entrypoint: true });
      });
    }

    return {
      entrypoints: entrypoints.slice(0, 4),
      coreModules: coreModules.slice(0, 8),
      testFiles: testFiles.slice(0, 6),
      configFiles: configFiles.slice(0, 4),
    };
  }, [arch, files]);

  // 2. Real import graph connections from arch.imports_graph
  const realDependencies = useMemo(() => {
    const graph = arch?.imports_graph || {};
    const entries = Object.entries(graph) as [string, string[]][];
    return entries.filter(([, imports]) => imports && imports.length > 0);
  }, [arch]);

  const filteredDependencies = useMemo(() => {
    if (!depSearch.trim()) return realDependencies;
    const q = depSearch.toLowerCase();
    return realDependencies.filter(([src, imps]) => {
      return (
        src.toLowerCase().includes(q) ||
        imps.some((imp) => imp.toLowerCase().includes(q))
      );
    });
  }, [realDependencies, depSearch]);

  // 3. File type breakdown from actual files
  const fileTypeDistribution = useMemo(() => {
    if (!files || files.length === 0) return [];
    const counts: Record<string, { count: number; bytes: number }> = {};
    files.forEach((f) => {
      const ext = f.path.includes(".") ? f.path.split(".").pop()!.toLowerCase() : "other";
      if (!counts[ext]) counts[ext] = { count: 0, bytes: 0 };
      counts[ext].count += 1;
      counts[ext].bytes += f.size_bytes || 0;
    });

    const total = files.length;
    return Object.entries(counts)
      .map(([ext, val]) => ({
        extension: `.${ext}`,
        count: val.count,
        percentage: Math.round((val.count / total) * 100),
        kb: Math.round((val.bytes / 1024) * 10) / 10,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 6);
  }, [files]);

  // 4. Symbol density from real AST data
  const topSymbolModules = useMemo(() => {
    const modules = arch?.modules || [];
    return [...modules]
      .map((m: any) => ({
        path: m.path,
        name: m.path.split("/").pop() || m.path,
        functionsCount: (m.functions || []).length,
        classesCount: (m.classes || []).length,
        isTest: m.is_test,
      }))
      .sort((a, b) => (b.functionsCount + b.classesCount) - (a.functionsCount + a.classesCount))
      .slice(0, 6);
  }, [arch]);

  // 5. Generated Mermaid code based strictly on actual repository data
  const dynamicMermaidCode = useMemo(() => {
    const entry = architectureLayers?.entrypoints[0]?.path || "app/main.py";
    const coreList = (architectureLayers?.coreModules || []).slice(0, 4);
    const testList = (architectureLayers?.testFiles || []).slice(0, 3);

    let code = `graph TD\n`;
    code += `    User([Contributor / User]) -->|Invoke| EP["${entry}"]\n`;
    coreList.forEach((m: any, idx: number) => {
      const cleanName = m.path.split("/").pop() || m.path;
      code += `    EP -->|Routes To| M${idx}["${cleanName}"]\n`;
    });
    testList.forEach((t: any, idx: number) => {
      const cleanTest = t.path.split("/").pop() || t.path;
      code += `    M0 -.->|Verified By| T${idx}["${cleanTest}"]\n`;
    });
    code += `    classDef entry fill:#f5f3ff,stroke:#7c3aed,stroke-width:2px,color:#1e1b4b;\n`;
    code += `    classDef module fill:#ffffff,stroke:#cbd5e1,stroke-width:1.5px,color:#0f172a;\n`;
    code += `    classDef test fill:#ecfdf5,stroke:#10b981,stroke-width:1.5px,color:#064e3b;\n`;
    code += `    class EP entry;\n`;
    coreList.forEach((_: any, idx: number) => {
      code += `    class M${idx} module;\n`;
    });
    testList.forEach((_: any, idx: number) => {
      code += `    class T${idx} test;\n`;
    });

    return code;
  }, [architectureLayers]);

  const hasAnalysisData = (files && files.length > 0) || (arch && arch.modules_count > 0);

  return (
    <div className="card p-6 sm:p-8 space-y-6">
      {/* Header & Tabs */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-gray-100 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-xl bg-brand-50 border border-brand-200/80 flex items-center justify-center text-brand-600 shadow-sm">
              <Network className="w-4 h-4" />
            </span>
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                Codebase Architecture &amp; Diagrams
              </h2>
              {repoData?.id && (
                <span className="text-[11px] font-mono text-gray-400 font-medium">
                  {repoData.id} {repoData.commit_sha ? `@${repoData.commit_sha.slice(0, 7)}` : ""}
                </span>
              )}
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Grounded architectural relationships, verified module imports, and contributor workflows derived strictly from static AST analysis.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-surface-100 p-1 rounded-2xl border border-gray-200/80 overflow-x-auto">
          {[
            { id: "architecture", label: "Architecture", icon: Layers },
            { id: "dependencies", label: "Dependencies", icon: Network },
            { id: "workflow",     label: "Workflow",     icon: GitBranch },
            { id: "mermaid",      label: "Mermaid",      icon: Code2 },
            { id: "composition",  label: "Composition",  icon: BarChart3 },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                id={`diagram-tab-${tab.id}`}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 shrink-0 ${
                  active
                    ? "bg-white text-brand-700 shadow-sm border border-brand-100/80 font-bold"
                    : "text-gray-500 hover:text-gray-900"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {!hasAnalysisData ? (
        <div className="text-center py-16 px-4 rounded-3xl bg-surface-50 border border-dashed border-gray-200 space-y-3">
          <Layers className="w-10 h-10 text-gray-400 mx-auto" />
          <h3 className="text-sm font-bold text-gray-700">No Architecture Analysis Data</h3>
          <p className="text-xs text-gray-500 max-w-md mx-auto">
            This repository has not been indexed yet. Analyze the repository on the home page or click &ldquo;Regenerate All Documentation&rdquo; in the Documentation tab.
          </p>
        </div>
      ) : (
        <>
          {/* TAB 1: ARCHITECTURE DIAGRAM */}
          {activeTab === "architecture" && (
            <div className="space-y-6 animate-in">
              <div className="notice-info">
                <Info className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
                <p className="text-xs text-sky-900">
                  <span className="font-bold">Verified AST Architecture:</span> Nodes represent real source modules identified in the repository snapshot. Arrows indicate request dispatch and test verification paths. Click any node to inspect discovered classes and functions.
                </p>
              </div>

              {/* Three-Tier Visual Flow with Connecting Arrows */}
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
                  {/* Tier 1: Entrypoints */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="section-label text-brand-700 flex items-center gap-1.5">
                        <Terminal className="w-3.5 h-3.5" /> 1. Entrypoints
                      </span>
                      <span className="text-[10px] text-gray-400 font-mono font-bold">
                        {architectureLayers?.entrypoints.length || 0} files
                      </span>
                    </div>

                    <div className="space-y-2.5">
                      {architectureLayers?.entrypoints && architectureLayers.entrypoints.length > 0 ? (
                        architectureLayers.entrypoints.map((ep: any, i: number) => (
                          <div
                            key={ep.path || i}
                            onClick={() => setSelectedNode(ep)}
                            className={`p-4 rounded-2xl border transition-all cursor-pointer relative ${
                              selectedNode?.path === ep.path
                                ? "bg-brand-50 border-brand-300 ring-2 ring-brand-200 shadow-md"
                                : "bg-white border-gray-200/90 hover:border-brand-200 shadow-sm hover:shadow"
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="badge-brand font-mono text-[9px]">ENTRYPOINT</span>
                              <span className="text-[10px] text-gray-400 font-mono">
                                {(ep.functions || []).length} fn
                              </span>
                            </div>
                            <p className="font-mono text-xs font-bold text-gray-900 truncate" title={ep.path}>
                              {ep.path}
                            </p>
                            {ep.classes && ep.classes.length > 0 && (
                              <p className="text-[10px] text-gray-500 mt-1 truncate">
                                Classes: {ep.classes.join(", ")}
                              </p>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="p-4 rounded-2xl bg-gray-50 border border-gray-200 text-xs text-gray-500 italic text-center">
                          Standard package layout (no single main entrypoint)
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Tier 2: Core Modules */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="section-label text-purple-700 flex items-center gap-1.5">
                        <Folder className="w-3.5 h-3.5" /> 2. Core Modules
                      </span>
                      <span className="text-[10px] text-gray-400 font-mono font-bold">
                        {architectureLayers?.coreModules.length || 0} indexed
                      </span>
                    </div>

                    <div className="space-y-2.5">
                      {architectureLayers?.coreModules && architectureLayers.coreModules.length > 0 ? (
                        architectureLayers.coreModules.slice(0, 5).map((m: any, i: number) => (
                          <div
                            key={m.path || i}
                            onClick={() => setSelectedNode(m)}
                            className={`p-4 rounded-2xl border transition-all cursor-pointer relative ${
                              selectedNode?.path === m.path
                                ? "bg-purple-50 border-purple-300 ring-2 ring-purple-200 shadow-md"
                                : "bg-white border-gray-200/90 hover:border-purple-200 shadow-sm hover:shadow"
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="badge-muted font-mono text-[9px]">MODULE</span>
                              <span className="text-[10px] text-gray-400 font-mono">
                                {(m.functions || []).length} fn, {(m.classes || []).length} cls
                              </span>
                            </div>
                            <p className="font-mono text-xs font-bold text-gray-900 truncate" title={m.path}>
                              {m.path}
                            </p>
                            {m.classes && m.classes.length > 0 && (
                              <p className="text-[10px] text-gray-500 mt-1 truncate">
                                Classes: {m.classes.join(", ")}
                              </p>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="p-4 rounded-2xl bg-gray-50 border border-gray-200 text-xs text-gray-500 italic text-center">
                          No indexed core modules found
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Tier 3: Test Suites */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="section-label text-emerald-700 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" /> 3. Test Suites &amp; Verification
                      </span>
                      <span className="text-[10px] text-gray-400 font-mono font-bold">
                        {architectureLayers?.testFiles.length || 0} files
                      </span>
                    </div>

                    <div className="space-y-2.5">
                      {architectureLayers?.testFiles && architectureLayers.testFiles.length > 0 ? (
                        architectureLayers.testFiles.map((t: any, i: number) => (
                          <div
                            key={t.path || i}
                            onClick={() => setSelectedNode(t)}
                            className={`p-4 rounded-2xl border transition-all cursor-pointer relative ${
                              selectedNode?.path === t.path
                                ? "bg-emerald-50 border-emerald-300 ring-2 ring-emerald-200 shadow-md"
                                : "bg-white border-gray-200/90 hover:border-emerald-200 shadow-sm hover:shadow"
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="badge-success font-mono text-[9px]">TEST SUITE</span>
                              <span className="text-[10px] text-emerald-600 font-mono font-bold">VERIFIABLE</span>
                            </div>
                            <p className="font-mono text-xs font-bold text-gray-900 truncate" title={t.path}>
                              {t.path}
                            </p>
                            <p className="text-[10px] text-gray-500 mt-1">
                              Target for sandbox test runs
                            </p>
                          </div>
                        ))
                      ) : (
                        <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200 text-xs text-amber-800 text-center">
                          No test files detected in indexed snapshot
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Flow Indicators / Arrows Legend */}
                <div className="flex flex-wrap items-center justify-center gap-6 py-3 px-4 rounded-2xl bg-surface-50 border border-gray-100 text-xs text-gray-600">
                  <span className="flex items-center gap-1.5 font-semibold">
                    <span className="w-2.5 h-0.5 bg-brand-500" />
                    <span>Entrypoint invokes Core Logic</span>
                    <ArrowRight className="w-3.5 h-3.5 text-brand-500" />
                  </span>
                  <span className="flex items-center gap-1.5 font-semibold">
                    <span className="w-2.5 h-0.5 border-t-2 border-dashed border-emerald-500" />
                    <span>Core Logic asserted by Test Suites</span>
                    <ArrowRight className="w-3.5 h-3.5 text-emerald-500" />
                  </span>
                </div>
              </div>

              {/* Node Inspector Drawer */}
              {selectedNode && (
                <div className="p-5 rounded-3xl bg-brand-50/70 border border-brand-200 animate-in space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileCode className="w-4 h-4 text-brand-600" />
                      <span className="font-mono text-xs font-bold text-gray-900">{selectedNode.path}</span>
                    </div>
                    <button
                      onClick={() => setSelectedNode(null)}
                      className="text-xs font-bold text-gray-400 hover:text-gray-700 px-2 py-1"
                    >
                      &times; Close
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    <div>
                      <p className="font-bold text-gray-700 mb-1.5">Classes Discovered:</p>
                      {selectedNode.classes && selectedNode.classes.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {selectedNode.classes.map((c: string) => (
                            <span key={c} className="badge-brand font-mono text-[11px]">{c}</span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-400 italic">No classes declared</p>
                      )}
                    </div>
                    <div>
                      <p className="font-bold text-gray-700 mb-1.5">Functions Discovered:</p>
                      {selectedNode.functions && selectedNode.functions.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {selectedNode.functions.map((f: string) => (
                            <span key={f} className="badge-muted font-mono text-[11px]">{f}()</span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-400 italic">No top-level functions declared</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: DEPENDENCY GRAPH */}
          {activeTab === "dependencies" && (
            <div className="space-y-5 animate-in">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="notice-info flex-1">
                  <Info className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
                  <p className="text-xs text-sky-900">
                    <span className="font-bold">Grounded Import Graph:</span> Displays explicit intra-codebase and standard module imports parsed by the AST engine. Arrows indicate dependency direction.
                  </p>
                </div>

                <div className="relative max-w-xs w-full">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                  <input
                    type="search"
                    value={depSearch}
                    onChange={(e) => setDepSearch(e.target.value)}
                    placeholder="Filter by module name…"
                    className="input pl-9 py-2 text-xs"
                  />
                </div>
              </div>

              {filteredDependencies.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredDependencies.map(([sourcePath, importedModules]) => (
                    <div
                      key={sourcePath}
                      className="p-5 rounded-3xl bg-white border border-gray-200/90 shadow-sm hover:border-brand-300 transition-all space-y-3"
                    >
                      <div className="flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-brand-600 shrink-0" />
                        <span className="font-mono text-xs font-bold text-gray-900 truncate" title={sourcePath}>
                          {sourcePath}
                        </span>
                      </div>

                      <div className="pl-4 border-l-2 border-brand-200/80 space-y-2">
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                          Imports ({importedModules.length}):
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {importedModules.map((imp) => (
                            <span
                              key={imp}
                              className="badge-muted font-mono text-[11px] flex items-center gap-1.5 py-1 px-2.5 bg-surface-50 border border-gray-200"
                            >
                              <ArrowRight className="w-3 h-3 text-brand-500 shrink-0" />
                              <span>{imp}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 px-4 rounded-3xl bg-surface-50 border border-gray-200 space-y-2">
                  <p className="text-sm font-bold text-gray-700">No Matching Module Imports</p>
                  <p className="text-xs text-gray-500 max-w-md mx-auto">
                    {depSearch
                      ? `No dependencies match '${depSearch}'.`
                      : "The analyzed priority files rely on standard library modules or self-contained logic."}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: WORKFLOW PIPELINE */}
          {activeTab === "workflow" && (
            <div className="space-y-6 animate-in">
              <div className="notice-info">
                <Info className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
                <p className="text-xs text-sky-900">
                  <span className="font-bold">FirstPatch 6-Stage Contribution Workflow:</span> Every beginner journey follows this verified lifecycle to prevent PR spam and guarantee claim safety.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {[
                  {
                    step: "1",
                    title: "Issue Triage & Scope",
                    desc: `Restate problem in contributor words, define actual vs expected behavior, and set decision gate (${issues.length > 0 ? `${issues.length} issues indexed` : "fresh triage"}).`,
                    badge: "TRIAGE GATE",
                    color: "border-brand-200 bg-brand-50/50 text-brand-700",
                    next: "AST Mapping",
                  },
                  {
                    step: "2",
                    title: "AST Evidence Grounding",
                    desc: "Map issue keywords to verified file paths, symbol declarations, and candidate line ranges.",
                    badge: "REALITY CHECK",
                    color: "border-purple-200 bg-purple-50/50 text-purple-700",
                    next: "Mentorship",
                  },
                  {
                    step: "3",
                    title: "Socratic Mentorship",
                    desc: "Explore architecture via Learn Mode or Copilot Mode without hallucinated repository facts.",
                    badge: "GROUNDED LLM",
                    color: "border-indigo-200 bg-indigo-50/50 text-indigo-700",
                    next: "Setup Doctor",
                  },
                  {
                    step: "4",
                    title: "Setup Failure Doctor",
                    desc: "Diagnose local virtualenv, missing packages, and config issues before writing any patch.",
                    badge: "DIAGNOSTICS",
                    color: "border-amber-200 bg-amber-50/50 text-amber-700",
                    next: "Sandbox Test",
                  },
                  {
                    step: "5",
                    title: "Verification Sandbox",
                    desc: "Run isolated local test suite with timeout and memory bounds to verify reproduction.",
                    badge: "SAFE TEST RUNNER",
                    color: "border-emerald-200 bg-emerald-50/50 text-emerald-700",
                    next: "Maintainer PR",
                  },
                  {
                    step: "6",
                    title: "Review & Maintainer Draft",
                    desc: "Simulate maintainer review, audit for secret leaks, and generate polite community PR drafts.",
                    badge: "PR POLISH",
                    color: "border-sky-200 bg-sky-50/50 text-sky-700",
                    next: "Ready to Ship",
                  },
                ].map((item) => (
                  <div
                    key={item.step}
                    className="p-5 rounded-3xl bg-white border border-gray-200/90 shadow-sm flex flex-col justify-between space-y-4"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${item.color}`}>
                          {item.badge}
                        </span>
                        <span className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-extrabold text-gray-700">
                          {item.step}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-gray-900 mb-1.5">{item.title}</h4>
                      <p className="text-xs text-gray-500 leading-relaxed">{item.desc}</p>
                    </div>

                    <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-[11px] font-semibold text-gray-400">
                      <span>Next: {item.next}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-brand-500" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: MERMAID CODE VIEW */}
          {activeTab === "mermaid" && (
            <div className="space-y-4 animate-in">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-gray-900">Mermaid Component Diagram Specification</h3>
                  <p className="text-xs text-gray-500">Dynamically generated from analyzed AST modules</p>
                </div>

                <button
                  onClick={() => {
                    navigator.clipboard.writeText(dynamicMermaidCode);
                    setCopiedMermaid(true);
                    setTimeout(() => setCopiedMermaid(false), 2000);
                  }}
                  className="btn-secondary text-xs py-1.5 px-3 rounded-xl inline-flex items-center gap-1.5"
                >
                  {copiedMermaid ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedMermaid ? "Copied" : "Copy Mermaid"}
                </button>
              </div>

              <pre className="p-5 rounded-3xl bg-gray-950 text-purple-200 font-mono text-xs overflow-x-auto border border-gray-800 leading-relaxed">
                {dynamicMermaidCode}
              </pre>
            </div>
          )}

          {/* TAB 5: COMPOSITION & DENSITY */}
          {activeTab === "composition" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in">
              {/* File Types breakdown */}
              <div className="card p-6">
                <p className="section-label mb-4 text-brand-700">File Type Breakdown</p>
                {fileTypeDistribution.length > 0 ? (
                  <div className="space-y-3.5">
                    {fileTypeDistribution.map((item) => (
                      <div key={item.extension}>
                        <div className="flex justify-between text-xs mb-1.5 font-semibold">
                          <span className="text-gray-800 font-mono font-bold">{item.extension}</span>
                          <span className="text-gray-500 font-normal">
                            {item.count} files ({item.percentage}%) &bull; {item.kb} KB
                          </span>
                        </div>
                        <div className="score-bar">
                          <div
                            className="score-fill bg-gradient-to-r from-brand-500 to-purple-500"
                            style={{ width: `${item.percentage}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">No file data available</p>
                )}
              </div>

              {/* Symbol density */}
              <div className="card p-6">
                <p className="section-label mb-4 text-purple-700">Top Modules by AST Symbol Density</p>
                {topSymbolModules.length > 0 ? (
                  <div className="space-y-3">
                    {topSymbolModules.map((m) => (
                      <div key={m.path} className="flex items-center justify-between text-xs p-3 rounded-2xl bg-surface-50 border border-gray-100">
                        <div className="min-w-0 pr-2">
                          <p className="font-mono font-bold text-gray-900 truncate" title={m.path}>
                            {m.name}
                          </p>
                          <p className="text-[10px] text-gray-400 truncate">{m.path}</p>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="badge-brand font-mono text-[10px]">{m.functionsCount} fn</span>
                          <span className="badge-muted font-mono text-[10px]">{m.classesCount} cls</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">No AST symbol statistics available</p>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
