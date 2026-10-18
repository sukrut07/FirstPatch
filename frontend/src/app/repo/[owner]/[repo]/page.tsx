"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  getRepository, 
  getRepositoryFiles, 
  getRepositoryFileContent, 
  getRepositoryArchitecture, 
  discoverIssues, 
  askMentor, 
  planContribution, 
  createContribution, 
  diagnoseSetupError,
  getRepositoryDocumentation,
  generateRepositoryDocumentation
} from "@/lib/api";
import { 
  Layers, 
  FileCode2, 
  Network, 
  Compass, 
  BookOpen, 
  Stethoscope, 
  Sparkles, 
  Star, 
  GitFork, 
  Terminal, 
  CheckCircle2, 
  ArrowRight, 
  ExternalLink, 
  Code, 
  AlertTriangle,
  Play,
  Copy,
  ChevronRight,
  ShieldCheck,
  FileText,
  Download
} from "lucide-react";

export default function RepoWorkspacePage({
  params,
}: {
  params: Promise<{ owner: string; repo: string }>;
}) {
  const resolvedParams = use(params);
  const { owner, repo } = resolvedParams;
  const repoId = `${owner}/${repo}`;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<"overview" | "architecture" | "files" | "issues" | "evidence" | "doctor" | "mentor" | "docs">("overview");
  const [repoData, setRepoData] = useState<any>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [arch, setArch] = useState<any>(null);
  const [issues, setIssues] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Documentation State
  const [docsData, setDocsData] = useState<any>(null);
  const [selectedDocKey, setSelectedDocKey] = useState<"project_overview" | "architecture" | "beginner_setup" | "contribution_guide">("project_overview");
  const [generatingDocs, setGeneratingDocs] = useState(false);
  const [copiedDoc, setCopiedDoc] = useState(false);

  // Mentor Chat State
  const [question, setQuestion] = useState("");
  const [mentorMode, setMentorMode] = useState<"learn" | "copilot">("learn");
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [asking, setAsking] = useState(false);

  // Setup Doctor State
  const [errorInput, setErrorInput] = useState("");
  const [diagnosis, setDiagnosis] = useState<any>(null);
  const [diagnosing, setDiagnosing] = useState(false);

  // Planning State
  const [planningIssue, setPlanningIssue] = useState<string | null>(null);

  useEffect(() => {
    loadRepoData();
  }, [owner, repo]);

  const loadRepoData = async () => {
    setLoading(true);
    try {
      const data = await getRepository(owner, repo);
      setRepoData(data);
      const fList = await getRepositoryFiles(owner, repo);
      setFiles(fList);
      if (fList.length > 0) {
        loadFile(fList[0].path);
      }
      const archData = await getRepositoryArchitecture(owner, repo);
      setArch(archData);
      const issuesData = await discoverIssues(repoId, "Beginner");
      setIssues(issuesData);
      try {
        const docsRes = await getRepositoryDocumentation(owner, repo);
        if (docsRes?.available_documents) setDocsData(docsRes.available_documents);
      } catch {}
    } catch {
      // Graceful fallback
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDocs = async () => {
    setGeneratingDocs(true);
    try {
      await generateRepositoryDocumentation(owner, repo);
      const docsRes = await getRepositoryDocumentation(owner, repo);
      if (docsRes?.available_documents) setDocsData(docsRes.available_documents);
    } catch (e: any) {
      alert("Failed to generate documentation: " + e.message);
    } finally {
      setGeneratingDocs(false);
    }
  };

  const handleCopyDoc = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedDoc(true);
    setTimeout(() => setCopiedDoc(false), 2000);
  };

  const loadFile = async (path: string) => {
    try {
      const fileDetail = await getRepositoryFileContent(owner, repo, path);
      setSelectedFile(fileDetail);
    } catch {}
  };

  const handleAskMentor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || asking) return;

    const userText = question;
    setQuestion("");
    setAsking(true);

    const newMsgs = [...chatMessages, { role: "user", content: userText }];
    setChatMessages(newMsgs);

    try {
      const res = await askMentor({
        repositoryId: repoId,
        question: userText,
        mode: mentorMode,
        skillLevel: "Beginner"
      });
      setChatMessages([...newMsgs, {
        role: "assistant",
        content: res.answer,
        evidence: res.evidence,
        model: res.model_used
      }]);
    } catch (err: any) {
      setChatMessages([...newMsgs, {
        role: "assistant",
        content: `Error generating response: ${err.message}`
      }]);
    } finally {
      setAsking(false);
    }
  };

  const handleDiagnose = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!errorInput.trim() || diagnosing) return;
    setDiagnosing(true);
    try {
      const res = await diagnoseSetupError(errorInput, repoData?.language || "Python");
      setDiagnosis(res);
    } catch {} finally {
      setDiagnosing(false);
    }
  };

  const handleStartContribution = async (issue: any) => {
    setPlanningIssue(issue.id);
    try {
      const planRes = await planContribution({
        repositoryId: repoId,
        issueTitle: issue.title,
        issueDescription: issue.body,
        issueId: issue.id
      });
      const ws = await createContribution({
        repositoryId: repoId,
        issueId: issue.id,
        title: issue.title,
        description: issue.body,
        steps: planRes.plan?.step_by_step_plan
      });
      router.push(`/contributions/${ws.workspace_id}`);
    } catch (e: any) {
      alert("Failed to start workspace: " + e.message);
    } finally {
      setPlanningIssue(null);
    }
  };

  const tabs = [
    { id: "overview", label: "Overview", icon: Layers },
    { id: "architecture", label: "Architecture", icon: Network },
    { id: "files", label: "File Explorer", icon: FileCode2 },
    { id: "issues", label: `Issues (${issues.length})`, icon: Compass },
    { id: "evidence", label: "Evidence Ledger", icon: ShieldCheck },
    { id: "docs", label: "Documentation", icon: BookOpen },
    { id: "doctor", label: "Setup Doctor", icon: Stethoscope },
    { id: "mentor", label: "AI Mentor", icon: Sparkles },
  ];

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <span className="h-7 w-7 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></span>
        <p className="text-xs text-zinc-400 font-mono">Parsing AST & indexing repository context...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Repo Header */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {repoData?.language || "Python"}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-400 border border-zinc-700">
                branch: {repoData?.default_branch || "main"}
              </span>
              <span className="text-xs text-zinc-500 font-mono hidden sm:inline">
                SHA: {repoData?.default_commit_sha?.slice(0, 7)}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-zinc-100 flex items-center gap-2">
              {repoId}
              <a href={repoData?.html_url} target="_blank" rel="noreferrer" className="text-zinc-500 hover:text-zinc-300">
                <ExternalLink className="h-4 w-4" />
              </a>
            </h1>
            <p className="text-xs text-zinc-400 mt-1 max-w-3xl">
              {repoData?.description || "No description provided."}
            </p>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setActiveTab("mentor")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-xs font-medium text-zinc-200 transition-colors cursor-pointer"
            >
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              Ask Mentor
            </button>
            <button
              onClick={() => setActiveTab("issues")}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer"
            >
              <Compass className="h-3.5 w-3.5" />
              Browse Issues
            </button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="mt-4 pt-4 border-t border-zinc-800/80 flex flex-wrap items-center gap-6 text-xs text-zinc-400">
          <span className="flex items-center gap-1.5">
            <Star className="h-3.5 w-3.5 text-amber-400" />
            <strong className="text-zinc-200">{repoData?.stars?.toLocaleString()}</strong> stars
          </span>
          <span className="flex items-center gap-1.5">
            <GitFork className="h-3.5 w-3.5" />
            <strong className="text-zinc-200">{repoData?.forks?.toLocaleString()}</strong> forks
          </span>
          <span className="flex items-center gap-1.5">
            <FileCode2 className="h-3.5 w-3.5 text-cyan-400" />
            <strong className="text-zinc-200">{repoData?.files_count || files.length}</strong> indexed files
          </span>
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <strong className="text-zinc-200">{repoData?.chunks_count || 0}</strong> verified chunks
          </span>
        </div>
      </div>

      {/* Workspace Tabs Navigation */}
      <div className="flex items-center gap-1 border-b border-zinc-800 overflow-x-auto pb-px">
        {tabs.map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                isActive
                  ? "border-emerald-500 text-emerald-400 bg-emerald-500/5"
                  : "border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
              <h3 className="text-sm font-semibold text-zinc-200 mb-3">Repository Reality Summary</h3>
              <p className="text-xs text-zinc-300 leading-relaxed mb-4">
                {repoData?.analysis_summary || "Parsed and indexed using Python AST extraction and SQLite FTS5 lexical engine."}
              </p>
              <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-400">
                <span className="text-amber-400 font-semibold block mb-1">Analysis Limitations:</span>
                {repoData?.analysis_limitations || "Bounded ingestion applied. Large binary bundles and lockfiles excluded."}
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
              <h3 className="text-sm font-semibold text-zinc-200 mb-3">Architecture Boundaries</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-[11px] font-mono text-emerald-400 block mb-1">Entrypoints</span>
                  <ul className="text-xs text-zinc-300 space-y-1">
                    {arch?.entrypoints?.map((e: string) => (
                      <li key={e} className="font-mono text-[11px] truncate">• {e}</li>
                    )) || <li>src/main.py</li>}
                  </ul>
                </div>
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-[11px] font-mono text-cyan-400 block mb-1">Test Suites</span>
                  <ul className="text-xs text-zinc-300 space-y-1">
                    {arch?.test_suite?.slice(0, 4).map((t: string) => (
                      <li key={t} className="font-mono text-[11px] truncate">• {t}</li>
                    )) || <li>tests/</li>}
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
              <h3 className="text-sm font-semibold text-zinc-200 mb-3">Metadata & Topics</h3>
              <div className="flex flex-wrap gap-1.5 mb-4">
                {repoData?.topics?.map((topic: string) => (
                  <span key={topic} className="px-2 py-0.5 rounded bg-zinc-800 text-[11px] font-mono text-zinc-400">
                    #{topic}
                  </span>
                ))}
              </div>
              <div className="text-xs text-zinc-400 space-y-2 border-t border-zinc-800 pt-3">
                <div>License: <strong className="text-zinc-200">{repoData?.license_name || "MIT"}</strong></div>
                <div>Default Branch: <strong className="text-zinc-200">{repoData?.default_branch || "main"}</strong></div>
                <div>Indexed Files: <strong className="text-zinc-200">{files.length}</strong></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Architecture Graph */}
      {activeTab === "architecture" && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">Module Dependency Hierarchy</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Extracted via AST import traces. Links high-level entrypoints to internal modules and tests.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {arch?.modules?.slice(0, 15).map((m: any) => (
              <div key={m.path} className="p-4 rounded-xl border border-zinc-800 bg-zinc-950/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-zinc-200 truncate">{m.path}</span>
                  {m.is_test ? (
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">TEST</span>
                  ) : m.is_entrypoint ? (
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">ENTRY</span>
                  ) : null}
                </div>

                {m.classes?.length > 0 && (
                  <div className="text-[11px] text-zinc-400">
                    <span className="text-zinc-500">Classes:</span> {m.classes.join(", ")}
                  </div>
                )}

                {m.functions?.length > 0 && (
                  <div className="text-[11px] text-zinc-400">
                    <span className="text-zinc-500">Functions:</span> {m.functions.slice(0, 4).join(", ")}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: File Explorer & Code Viewer */}
      {activeTab === "files" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-[500px]">
          {/* File Tree List */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-3 space-y-1 overflow-y-auto max-h-[600px]">
            <div className="px-3 py-2 text-xs font-semibold text-zinc-400 uppercase tracking-wider font-mono">
              Indexed Files ({files.length})
            </div>
            {files.map((f) => (
              <button
                key={f.path}
                onClick={() => loadFile(f.path)}
                className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-mono transition-colors text-left cursor-pointer ${
                  selectedFile?.path === f.path
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
              >
                <span className="truncate">{f.path}</span>
                {f.is_test ? (
                  <span className="text-[10px] text-cyan-400 font-sans">test</span>
                ) : null}
              </button>
            ))}
          </div>

          {/* Code Viewer Panel */}
          <div className="lg:col-span-2 rounded-xl border border-zinc-800 bg-zinc-950 p-4 flex flex-col justify-between">
            {selectedFile ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                  <div>
                    <span className="font-mono text-xs font-bold text-zinc-200">{selectedFile.path}</span>
                    <span className="text-[11px] text-zinc-500 ml-2">({selectedFile.size_bytes} bytes)</span>
                  </div>
                  <a
                    href={`https://github.com/${repoId}/blob/${repoData?.default_commit_sha || 'main'}/${selectedFile.path}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-emerald-400 hover:underline flex items-center gap-1 font-mono"
                  >
                    GitHub Source <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                {/* AST Symbols Extracted */}
                {selectedFile.parsed_metadata?.symbols?.length > 0 && (
                  <div className="p-2.5 rounded-lg bg-zinc-900/80 border border-zinc-800 text-xs">
                    <span className="text-zinc-400 font-semibold block mb-1">AST Symbols Detected:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedFile.parsed_metadata.symbols.slice(0, 10).map((s: any, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 rounded bg-zinc-800 text-[10px] font-mono text-emerald-300">
                          {s.type} {s.name} (L{s.line_start}-{s.line_end})
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Raw Code Content with Lines */}
                <div className="overflow-x-auto max-h-[450px] font-mono text-xs bg-zinc-950 p-3 rounded-lg border border-zinc-800/80">
                  <pre className="text-zinc-300 leading-relaxed">
                    {selectedFile.content ? (
                      selectedFile.content.split("\n").map((line: string, i: number) => (
                        <div key={i} className="table-row">
                          <span className="table-cell pr-4 select-none text-zinc-600 text-right">{i + 1}</span>
                          <span className="table-cell whitespace-pre">{line}</span>
                        </div>
                      ))
                    ) : (
                      "File content empty or unavailable."
                    )}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="text-center py-20 text-xs text-zinc-500">
                Select a file from the tree to view parsed AST code.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Issue Explorer */}
      {activeTab === "issues" && (
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">Candidate Open-Source Issues</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Ranked by transparent fit heuristics, prerequisite detection, and codebase complexity.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {issues.map((issue) => {
              const rec = issue.recommendation;
              const isPlanning = planningIssue === issue.id;
              return (
                <div
                  key={issue.id}
                  className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 flex flex-col justify-between hover:border-zinc-700 transition-all space-y-4"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span className="text-xs font-mono text-zinc-500">#{issue.number}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {rec?.fit_score}% FIT ({rec?.estimated_complexity || "Beginner"})
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-zinc-200 mb-2">{issue.title}</h4>
                    <p className="text-xs text-zinc-400 line-clamp-3 mb-3 leading-relaxed">
                      {issue.body || "No issue description provided."}
                    </p>

                    {/* Labels */}
                    <div className="flex flex-wrap gap-1 mb-3">
                      {issue.labels?.map((l: string) => (
                        <span key={l} className="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] font-mono text-zinc-400">
                          {l}
                        </span>
                      ))}
                    </div>

                    {/* Reasons & Prerequisites */}
                    {rec?.reasons?.length > 0 && (
                      <div className="text-[11px] text-zinc-300 bg-zinc-950/60 p-2.5 rounded-lg border border-zinc-800/80 mb-2">
                        <strong className="text-emerald-400 block mb-1">Why this matches:</strong>
                        <ul className="space-y-0.5">
                          {rec.reasons.slice(0, 2).map((r: string, idx: number) => (
                            <li key={idx} className="flex items-start gap-1">
                              <span className="text-emerald-400">•</span> {r}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {rec?.prerequisite_skills?.length > 0 && (
                      <div className="text-[11px] text-zinc-400">
                        <span className="text-zinc-500">Prerequisites:</span> {rec.prerequisite_skills.join(", ")}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="border-t border-zinc-800 pt-3 flex items-center justify-between">
                    <a
                      href={issue.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 font-mono"
                    >
                      Original Issue <ExternalLink className="h-3 w-3" />
                    </a>

                    <button
                      onClick={() => handleStartContribution(issue)}
                      disabled={isPlanning}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer disabled:opacity-50"
                    >
                      {isPlanning ? (
                        <>
                          <span className="h-3 w-3 border-2 border-zinc-950 border-t-transparent rounded-full animate-spin"></span>
                          Generating Plan...
                        </>
                      ) : (
                        <>
                          Start Contribution Plan
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
      )}

      {/* Tab 5: Evidence Ledger */}
      {activeTab === "evidence" && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">Verifiable Grounding Ledger</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Deterministic source records parsed by Python AST and indexed with SQLite FTS5. Every AI claim links directly to these verified line coordinates.
            </p>
          </div>

          <div className="space-y-3">
            {files.map((f) => (
              <div key={f.id} className="p-3.5 rounded-lg border border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
                <div>
                  <span className="font-mono text-xs font-bold text-zinc-200">{f.path}</span>
                  <span className="text-[11px] text-zinc-500 ml-2">({f.file_type || "code"})</span>
                  <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                    commit: {repoData?.default_commit_sha?.slice(0, 7)} • status: verified AST
                  </p>
                </div>
                <a
                  href={`https://github.com/${repoId}/blob/${repoData?.default_commit_sha || 'main'}/${f.path}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-emerald-400 hover:underline flex items-center gap-1 font-mono"
                >
                  Verify on GitHub <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 6: Setup Failure Doctor */}
      {activeTab === "doctor" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <Stethoscope className="h-4 w-4 text-emerald-400" />
                Setup Failure Doctor
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Paste any terminal installation error, pip failure, or npm traceback to diagnose the root cause and get safe fix commands.
              </p>
            </div>

            <form onSubmit={handleDiagnose} className="space-y-3">
              <textarea
                rows={8}
                placeholder="Paste stderr or traceback output here (e.g. ModuleNotFoundError: No module named 'flask')..."
                value={errorInput}
                onChange={(e) => setErrorInput(e.target.value)}
                className="w-full p-3 rounded-lg border border-zinc-800 bg-zinc-950 font-mono text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
              />
              <button
                type="submit"
                disabled={diagnosing || !errorInput.trim()}
                className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer disabled:opacity-50"
              >
                {diagnosing ? "Diagnosing..." : "Diagnose Error"}
              </button>
            </form>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-zinc-200">Diagnosis & Remediation</h3>
            {diagnosis ? (
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-[10px] font-mono text-zinc-500 block uppercase">Error Category</span>
                  <span className="text-xs font-bold text-amber-400">{diagnosis.category}</span>
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-semibold text-zinc-300">Actionable Remediation Commands:</span>
                  {diagnosis.remediation_plan?.map((plan: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <code className="text-xs font-mono text-emerald-300 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          {plan.command}
                        </code>
                        <button
                          onClick={() => navigator.clipboard.writeText(plan.command)}
                          className="text-[10px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1 cursor-pointer"
                        >
                          <Copy className="h-3 w-3" /> Copy
                        </button>
                      </div>
                      <p className="text-[11px] text-zinc-400">{plan.explanation}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-16 text-xs text-zinc-500">
                Paste an error log to receive a step-by-step diagnostic breakdown.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 7: AI Mentor (Chat) */}
      {activeTab === "mentor" && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div>
              <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-emerald-400" />
                Repository-Grounded AI Mentor
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Every answer references verified source files, line ranges, and AST definitions.
              </p>
            </div>

            {/* Mode Toggle */}
            <div className="flex items-center gap-1 bg-zinc-950 p-1 rounded-lg border border-zinc-800">
              <button
                onClick={() => setMentorMode("learn")}
                className={`px-3 py-1 rounded text-xs font-medium cursor-pointer transition-colors ${
                  mentorMode === "learn"
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Learn Mode (Socratic)
              </button>
              <button
                onClick={() => setMentorMode("copilot")}
                className={`px-3 py-1 rounded text-xs font-medium cursor-pointer transition-colors ${
                  mentorMode === "copilot"
                    ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Copilot Mode (Direct)
              </button>
            </div>
          </div>

          {/* Chat Messages */}
          <div className="space-y-4 min-h-[300px] max-h-[500px] overflow-y-auto p-3 rounded-lg bg-zinc-950/60 border border-zinc-800/80">
            {chatMessages.length === 0 ? (
              <div className="text-center py-16 text-xs text-zinc-500">
                Ask a question about this repository (e.g. &quot;How does the request routing work?&quot; or &quot;Where are the unit tests located?&quot;).
              </div>
            ) : (
              chatMessages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-xl text-xs space-y-2 leading-relaxed ${
                    msg.role === "user"
                      ? "bg-zinc-900 border border-zinc-800 text-zinc-200 ml-auto max-w-xl"
                      : "bg-zinc-950 border border-zinc-800 text-zinc-300 max-w-3xl"
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono mb-1">
                    <span>{msg.role === "user" ? "You" : `FirstPatch Mentor (${msg.model || 'Local Model'})`}</span>
                  </div>
                  <div className="whitespace-pre-wrap">{msg.content}</div>

                  {msg.evidence?.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-zinc-800/80">
                      <span className="text-[10px] font-mono text-emerald-400 block mb-1">VERIFIED GROUNDED CITATIONS:</span>
                      <div className="space-y-1">
                        {msg.evidence.map((ev: any) => (
                          <div key={ev.id} className="text-[11px] font-mono text-zinc-400 flex items-center justify-between">
                            <span>• {ev.file_path} (L{ev.start_line}-L{ev.end_line})</span>
                            <a href={ev.source_url} target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline flex items-center gap-1">
                              View GitHub <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Chat Input */}
          <form onSubmit={handleAskMentor} className="flex gap-2">
            <input
              type="text"
              placeholder={`Ask in ${mentorMode === 'learn' ? 'Learn' : 'Copilot'} Mode (e.g. Where is configuration handled?)...`}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="flex-1 p-2.5 rounded-lg border border-zinc-800 bg-zinc-950 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
              disabled={asking}
            />
            <button
              type="submit"
              disabled={asking || !question.trim()}
              className="px-4 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer disabled:opacity-50 shrink-0"
            >
              {asking ? "Reasoning..." : "Send"}
            </button>
          </form>
        </div>
      )}

      {/* DOCUMENTATION TAB */}
      {activeTab === "docs" && (
        <div className="space-y-6">
          {/* Docs Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <div>
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-emerald-400" />
                <h2 className="text-sm font-semibold text-zinc-200">
                  Standardized Repository Documentation
                </h2>
              </div>
              <p className="text-xs text-zinc-400 mt-1 max-w-2xl">
                Deterministic markdown files emitted to <code className="text-emerald-400 font-mono text-[11px]">docs/generated/</code> summarizing project mission, Mermaid component dataflow, local setup, and PR conventions.
              </p>
            </div>
            <button
              onClick={handleGenerateDocs}
              disabled={generatingDocs}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer disabled:opacity-50 shrink-0 self-start sm:self-auto"
            >
              {generatingDocs ? (
                <>
                  <span className="h-3 w-3 border-2 border-zinc-950 border-t-transparent rounded-full animate-spin"></span>
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" />
                  {docsData ? "Regenerate Docs" : "Generate Documentation"}
                </>
              )}
            </button>
          </div>

          {/* Document Selector Pills */}
          <div className="flex flex-wrap items-center gap-2">
            {[
              { key: "project_overview", label: "📖 Project Overview", file: "PROJECT_OVERVIEW.md" },
              { key: "architecture", label: "🏗️ Architecture & Dataflow", file: "ARCHITECTURE.md" },
              { key: "beginner_setup", label: "🛠️ Beginner Setup Guide", file: "BEGINNER_SETUP.md" },
              { key: "contribution_guide", label: "📜 Contribution Guide", file: "CONTRIBUTION_GUIDE.md" },
            ].map((doc) => {
              const isSelected = selectedDocKey === doc.key;
              const isAvailable = Boolean(docsData?.[doc.key]);
              return (
                <button
                  key={doc.key}
                  onClick={() => setSelectedDocKey(doc.key as any)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                    isSelected
                      ? "border-emerald-500 bg-emerald-500/10 text-emerald-300 font-semibold"
                      : "border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                  }`}
                >
                  <span>{doc.label}</span>
                  {isAvailable && (
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Document Content Box */}
          {docsData && docsData[selectedDocKey] ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-950 border-b border-zinc-800 text-xs">
                <span className="font-mono text-zinc-400 flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-emerald-400" />
                  docs/generated/{selectedDocKey === "project_overview" ? "PROJECT_OVERVIEW.md" : selectedDocKey === "architecture" ? "ARCHITECTURE.md" : selectedDocKey === "beginner_setup" ? "BEGINNER_SETUP.md" : "CONTRIBUTION_GUIDE.md"}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleCopyDoc(docsData[selectedDocKey])}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-mono transition-colors cursor-pointer"
                  >
                    <Copy className="h-3 w-3" />
                    {copiedDoc ? "Copied!" : "Copy Markdown"}
                  </button>
                  <a
                    href={`data:text/markdown;charset=utf-8,${encodeURIComponent(docsData[selectedDocKey])}`}
                    download={`${selectedDocKey}.md`}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-mono transition-colors cursor-pointer"
                  >
                    <Download className="h-3 w-3" />
                    Download
                  </a>
                </div>
              </div>

              <div className="p-5 font-mono text-xs text-zinc-200 whitespace-pre-wrap leading-relaxed overflow-x-auto max-h-[600px] bg-zinc-950/70">
                {docsData[selectedDocKey]}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-900/20 p-12 text-center space-y-4">
              <div className="h-12 w-12 rounded-xl bg-zinc-800/80 border border-zinc-700 flex items-center justify-center mx-auto text-emerald-400">
                <BookOpen className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-zinc-200">
                  Documentation Not Generated Yet
                </h3>
                <p className="text-xs text-zinc-400 max-w-md mx-auto">
                  Click below to synthesize AST symbols, directory layout, test structure, and contribution rules into clean, exportable Markdown documents.
                </p>
              </div>
              <button
                onClick={handleGenerateDocs}
                disabled={generatingDocs}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer disabled:opacity-50"
              >
                {generatingDocs ? "Synthesizing Documentation..." : "Generate Repository Documentation"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
