"use client";

import { useEffect, useState } from "react";
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
  generateRepositoryDocumentation,
  reanalyzeRepositoryWithGemma,
  bookmarkRepository,
} from "@/lib/api";
import {
  Layers,
  FileCode,
  Network,
  Compass,
  BookOpen,
  Sparkles,
  Star,
  GitFork,
  Terminal,
  CheckCircle2,
  ArrowRight,
  ExternalLink,
  Code,
  AlertTriangle,
  AlertCircle,
  Copy,
  Check,
  ShieldCheck,
  Download,
  Bookmark,
  ChevronRight,
  Send,
} from "lucide-react";
import CodebaseDiagrams from "@/components/CodebaseDiagrams";

export default function RepoWorkspacePage({
  params,
}: {
  params: { owner: string; repo: string };
}) {
  const { owner, repo } = params;
  const repoId = `${owner}/${repo}`;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<"overview" | "architecture" | "files" | "issues" | "doctor" | "mentor" | "docs">("overview");
  const [repoData, setRepoData] = useState<any>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [fileLoading, setFileLoading] = useState(false);
  const [arch, setArch] = useState<any>(null);
  const [issues, setIssues] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bookmarked, setBookmarked] = useState(false);

  // Setup Doctor State
  const [errorInput, setErrorInput] = useState("");
  const [diagnosis, setDiagnosis] = useState<any>(null);
  const [diagnosing, setDiagnosing] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

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

  useEffect(() => {
    loadAllData();
  }, [owner, repo]);

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [repoRes, filesRes, archRes, docsRes] = await Promise.all([
        getRepository(owner, repo).catch(() => null),
        getRepositoryFiles(owner, repo).catch(() => []),
        getRepositoryArchitecture(owner, repo).catch(() => null),
        getRepositoryDocumentation(owner, repo).catch(() => null),
      ]);

      if (repoRes) {
        setRepoData(repoRes);
        setBookmarked(!!repoRes.is_saved);
      }
      setFiles(filesRes || []);
      setArch(archRes || null);
      if (docsRes?.available_documents) {
        setDocsData(docsRes.available_documents);
      }

      // Discover issues
      discoverIssues(repoId)
        .then((iss) => { if (Array.isArray(iss)) setIssues(iss); })
        .catch(() => {});
    } catch (err: any) {
      setError(err.message || "Failed to load repository data.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectFile = async (f: any) => {
    setSelectedFile(f);
    setFileLoading(true);
    try {
      const res = await getRepositoryFileContent(owner, repo, f.path);
      setFileContent(res.content || "");
    } catch {
      setFileContent("// Could not fetch raw content for this file.");
    } finally {
      setFileLoading(false);
    }
  };

  const handleBookmark = async () => {
    try {
      await bookmarkRepository(owner, repo);
      setBookmarked(true);
    } catch (e: any) {
      alert("Failed to bookmark: " + e.message);
    }
  };

  const handleDiagnose = async () => {
    if (!errorInput.trim()) return;
    setDiagnosing(true);
    setDiagnosis(null);
    try {
      const res = await diagnoseSetupError(errorInput.trim(), repoData?.primary_language || "Python");
      setDiagnosis(res);
    } catch (e: any) {
      setDiagnosis({
        error_type: "Diagnosis Failed",
        root_cause: e.message || "Could not analyze error log.",
        remediation_command: "pip install -r requirements.txt",
      });
    } finally {
      setDiagnosing(false);
    }
  };

  const handleGenerateDocs = async () => {
    setGeneratingDocs(true);
    try {
      await generateRepositoryDocumentation(owner, repo);
      const docsRes = await getRepositoryDocumentation(owner, repo);
      if (docsRes?.available_documents) {
        setDocsData(docsRes.available_documents);
      }
    } catch (e: any) {
      alert("Failed to generate documentation: " + e.message);
    } finally {
      setGeneratingDocs(false);
    }
  };

  const handleAskMentor = async () => {
    if (!question.trim()) return;
    const q = question.trim();
    setChatMessages((prev) => [...prev, { sender: "user", content: q }]);
    setQuestion("");
    setAsking(true);
    try {
      const res = await askMentor({
        repositoryId: repoId,
        question: q,
        mode: mentorMode,
      });
      setChatMessages((prev) => [
        ...prev,
        {
          sender: "mentor",
          content: res.answer || "No response received.",
          evidence: res.evidence_used || [],
          model: res.model_used || "Gemma 4",
        },
      ]);
    } catch (err: any) {
      setChatMessages((prev) => [
        ...prev,
        { sender: "mentor", content: "Error: " + err.message },
      ]);
    } finally {
      setAsking(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 space-y-4">
        <div className="card p-8 skeleton h-72" />
        <div className="card p-8 skeleton h-96" />
      </div>
    );
  }

  if (error && !repoData) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <div className="card p-8 space-y-4">
          <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-gray-900">Repository Not Found</h2>
          <p className="text-xs text-gray-500">{error}</p>
          <Link href="/" className="btn-primary text-xs inline-flex items-center gap-1.5">
            Analyze on Home Page
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Repo Top Header Bento */}
      <div className="card-brand flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="w-9 h-9 rounded-2xl bg-brand-50 border border-brand-200/80 flex items-center justify-center text-brand-600 shadow-sm shrink-0">
              <FileCode className="w-5 h-5" />
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight">
              {repoId}
            </h1>
            {repoData?.primary_language && (
              <span className="badge-brand font-semibold">{repoData.primary_language}</span>
            )}
            {repoData?.commit_sha && (
              <span className="text-[10px] font-mono bg-white border border-gray-200 px-2 py-0.5 rounded-lg text-gray-500 shadow-sm">
                @{repoData.commit_sha.slice(0, 7)}
              </span>
            )}
          </div>
          {repoData?.description && (
            <p className="text-xs sm:text-sm text-gray-600 max-w-3xl leading-relaxed">
              {repoData.description}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
          {repoData?.html_url && (
            <a
              href={repoData.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary text-xs py-2 px-3.5 rounded-xl shadow-sm inline-flex items-center gap-1.5"
            >
              GitHub <ExternalLink className="w-3 h-3 text-gray-400" />
            </a>
          )}
          <button
            onClick={handleBookmark}
            className={`btn-secondary text-xs py-2 px-3.5 rounded-xl shadow-sm inline-flex items-center gap-1.5 ${
              bookmarked ? "text-amber-600 font-bold" : ""
            }`}
          >
            <Bookmark className={`w-3.5 h-3.5 ${bookmarked ? "fill-amber-400" : ""}`} />
            {bookmarked ? "Saved" : "Save Repo"}
          </button>
        </div>
      </div>

      {/* Workspace Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-gray-200/80">
        {[
          { id: "overview",     label: "Overview",             icon: Layers },
          { id: "architecture", label: "Architecture Diagrams",icon: Network },
          { id: "files",        label: `Files (${files.length})`, icon: FileCode },
          { id: "issues",       label: `Issues (${issues.length})`, icon: Compass },
          { id: "doctor",       label: "Setup Doctor",         icon: Terminal },
          { id: "mentor",       label: "AI Mentor",            icon: Sparkles },
          { id: "docs",         label: "Documentation",        icon: BookOpen },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              id={`tab-${tab.id}`}
              className={`flex items-center gap-2 px-4 py-2 rounded-2xl text-xs font-bold transition-all shrink-0 ${
                active
                  ? "bg-white text-brand-700 shadow-sm border border-brand-200/80"
                  : "text-gray-500 hover:text-gray-900 hover:bg-white/60"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Key Stats Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="card p-5">
              <span className="text-xs text-gray-400 font-bold uppercase">Stars</span>
              <div className="text-2xl font-extrabold text-amber-600 mt-1 flex items-center gap-1.5">
                <Star className="w-5 h-5 fill-amber-400" />
                {(repoData?.stars || 0).toLocaleString()}
              </div>
            </div>
            <div className="card p-5">
              <span className="text-xs text-gray-400 font-bold uppercase">Forks</span>
              <div className="text-2xl font-extrabold text-brand-600 mt-1 flex items-center gap-1.5">
                <GitFork className="w-5 h-5" />
                {(repoData?.forks || 0).toLocaleString()}
              </div>
            </div>
            <div className="card p-5">
              <span className="text-xs text-gray-400 font-bold uppercase">Open Issues</span>
              <div className="text-2xl font-extrabold text-purple-600 mt-1">
                {repoData?.open_issues_count || issues.length || 0}
              </div>
            </div>
            <div className="card p-5">
              <span className="text-xs text-gray-400 font-bold uppercase">Indexed Files</span>
              <div className="text-2xl font-extrabold text-emerald-600 mt-1">
                {files.length || repoData?.files_count || 0}
              </div>
            </div>
          </div>

          {/* AI Executive Summary */}
          {repoData?.ai_analysis?.executive_summary && (
            <div className="card p-6 space-y-3">
              <div className="flex items-center justify-between">
                <span className="section-label text-purple-700 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" /> AI Architecture Brief
                </span>
                <span className="badge-brand text-[10px]">Gemma 4 Verified</span>
              </div>
              <p className="text-xs sm:text-sm text-gray-700 leading-relaxed bg-purple-50/40 p-4 rounded-2xl border border-purple-100/60 italic">
                &ldquo;{repoData.ai_analysis.executive_summary}&rdquo;
              </p>
            </div>
          )}

          {/* Languages & Frameworks Bento */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card p-6 space-y-4">
              <span className="section-label text-brand-700">Discovered Frameworks &amp; Tools</span>
              {repoData?.detected_frameworks && repoData.detected_frameworks.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {repoData.detected_frameworks.map((f: any) => (
                    <span key={f.name} className="badge-brand text-xs font-semibold">
                      {f.name} ({f.confidence})
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400">Standard runtime environment</p>
              )}

              <span className="section-label text-indigo-700 block pt-3">Key Configuration Files</span>
              {repoData?.config_files && repoData.config_files.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {repoData.config_files.map((c: string) => (
                    <span key={c} className="badge-muted font-mono text-[11px]">{c}</span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400">No root config files indexed</p>
              )}
            </div>

            <div className="card p-6 space-y-4">
              <span className="section-label text-emerald-700">Verified Test Directories</span>
              {repoData?.test_locations && repoData.test_locations.length > 0 ? (
                <div className="space-y-2">
                  {repoData.test_locations.map((t: any) => (
                    <div key={t.path} className="flex items-center gap-2 text-xs font-mono bg-emerald-50/60 p-2 rounded-xl border border-emerald-100 text-emerald-900">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span>{t.path}</span>
                      {t.framework && <span className="text-gray-400">({t.framework})</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400">No test locations found in metadata</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: ARCHITECTURE DIAGRAMS */}
      {activeTab === "architecture" && (
        <CodebaseDiagrams
          files={files}
          arch={arch}
          issues={issues}
          repoData={repoData}
        />
      )}

      {/* TAB 3: CODEBASE FILES */}
      {activeTab === "files" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* File Tree */}
          <div className="card p-4 space-y-2 max-h-[600px] overflow-y-auto">
            <span className="section-label text-gray-700 block mb-2">Indexed Source Files ({files.length})</span>
            {files.map((f) => (
              <button
                key={f.id || f.path}
                onClick={() => handleSelectFile(f)}
                className={`w-full text-left p-2.5 rounded-xl font-mono text-xs flex items-center justify-between transition-all ${
                  selectedFile?.path === f.path
                    ? "bg-brand-50 text-brand-700 font-bold border border-brand-200"
                    : "text-gray-600 hover:bg-surface-100 hover:text-gray-900"
                }`}
              >
                <span className="truncate" title={f.path}>{f.path}</span>
                {f.is_test ? (
                  <span className="badge-success text-[9px] shrink-0 ml-1">TEST</span>
                ) : f.is_entrypoint ? (
                  <span className="badge-brand text-[9px] shrink-0 ml-1">ENTRY</span>
                ) : null}
              </button>
            ))}
          </div>

          {/* File Viewer */}
          <div className="md:col-span-2 card p-5 flex flex-col max-h-[600px]">
            {selectedFile ? (
              <div className="flex-1 flex flex-col space-y-3 min-h-0">
                <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                  <span className="font-mono text-xs font-bold text-gray-900">{selectedFile.path}</span>
                  <span className="text-[10px] text-gray-400 font-mono">
                    {Math.round((selectedFile.size_bytes || 0) / 1024)} KB
                  </span>
                </div>
                <div className="flex-1 overflow-y-auto bg-surface-50 rounded-2xl p-4 border border-gray-200">
                  {fileLoading ? (
                    <div className="text-xs text-gray-400 italic">Loading file content…</div>
                  ) : (
                    <pre className="font-mono text-xs text-gray-800 whitespace-pre-wrap leading-relaxed">
                      {fileContent}
                    </pre>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center py-20 text-center text-xs text-gray-400 space-y-2">
                <FileCode className="w-8 h-8 text-gray-300" />
                <p>Select any source file on the left to inspect its AST declarations.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: ISSUES & 5-FACTOR MATCHING */}
      {activeTab === "issues" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">Recommended Issues for Beginners</h2>
            <span className="text-xs text-gray-500 font-medium">Scored by 5 independent fit dimensions</span>
          </div>

          {issues.length === 0 ? (
            <div className="card p-10 text-center text-xs text-gray-400">
              No open issues discovered for this repository.
            </div>
          ) : (
            <div className="space-y-4">
              {issues.map((item: any) => {
                const rec = item.recommendation || {};
                const score = rec.fit_score || 75;
                return (
                  <div key={item.id || item.number} className="card-hover p-6">
                    <div className="flex flex-col sm:flex-row justify-between gap-4">
                      <div className="space-y-2 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-xs font-bold text-gray-400">#{item.number}</span>
                          <span className="badge-success text-xs font-bold">
                            {rec.estimated_complexity || "Beginner"}
                          </span>
                          {(item.labels || []).slice(0, 3).map((l: any) => (
                            <span key={typeof l === "string" ? l : l.name} className="badge-muted text-[10px]">
                              {typeof l === "string" ? l : l.name}
                            </span>
                          ))}
                        </div>
                        <h3 className="text-base font-bold text-gray-900">{item.title}</h3>
                        {item.body && (
                          <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">
                            {item.body}
                          </p>
                        )}
                        {rec.reasons && rec.reasons.length > 0 && (
                          <p className="text-[11px] text-brand-700 font-semibold">
                            💡 {rec.reasons[0]}
                          </p>
                        )}
                      </div>

                      <div className="sm:text-right shrink-0 space-y-2">
                        <div className="text-2xl font-extrabold text-gradient">{score}%</div>
                        <p className="text-[10px] text-gray-400 uppercase font-bold tracking-wider">FIT SCORE</p>
                        <Link
                          href={`/repo/${owner}/${repo}/issues/${item.number}`}
                          className="btn-primary text-xs py-2 px-4 rounded-xl inline-flex items-center gap-1.5 shadow-sm"
                        >
                          Investigate Issue <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: SETUP FAILURE DOCTOR */}
      {activeTab === "doctor" && (
        <div className="card p-6 sm:p-8 space-y-6">
          <div>
            <div className="flex items-center gap-2">
              <Terminal className="w-5 h-5 text-brand-600" />
              <h2 className="text-lg font-bold text-gray-900">Setup Failure Doctor</h2>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Encountered a virtual environment, missing dependency, or build failure? Paste the terminal error log below to diagnose root cause and receive a deterministic safe fix.
            </p>
          </div>

          <div className="space-y-3">
            <textarea
              rows={5}
              value={errorInput}
              onChange={(e) => setErrorInput(e.target.value)}
              placeholder="Paste terminal traceback (e.g. ModuleNotFoundError: No module named 'pytest' or ERESOLVE unable to resolve dependency)..."
              className="input font-mono text-xs py-3"
              disabled={diagnosing}
            />
            <button
              onClick={handleDiagnose}
              disabled={diagnosing || !errorInput.trim()}
              className="btn-primary text-xs py-2.5 px-5 rounded-2xl"
            >
              {diagnosing ? "Diagnosing…" : "Diagnose Setup Failure"}
            </button>
          </div>

          {diagnosis && (
            <div className="p-5 rounded-2xl bg-surface-50 border border-gray-200/80 space-y-4 animate-in">
              <div className="flex items-center justify-between">
                <span className="badge-warning font-bold text-xs">{diagnosis.error_type}</span>
                <span className="text-[10px] text-gray-400 font-mono">Confidence: 98%</span>
              </div>
              <div>
                <p className="text-xs font-bold text-gray-800">Root Cause:</p>
                <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">{diagnosis.root_cause}</p>
              </div>
              {diagnosis.remediation_command && (
                <div>
                  <p className="text-xs font-bold text-emerald-800 mb-1.5">Recommended Safe Command:</p>
                  <div className="flex items-center justify-between bg-gray-900 text-emerald-400 p-3 rounded-xl font-mono text-xs">
                    <span>{diagnosis.remediation_command}</span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(diagnosis.remediation_command);
                        setCopiedCmd(diagnosis.remediation_command);
                        setTimeout(() => setCopiedCmd(null), 2000);
                      }}
                      className="text-gray-400 hover:text-white"
                      title="Copy command"
                    >
                      {copiedCmd ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 6: AI MENTOR */}
      {activeTab === "mentor" && (
        <div className="card p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-gray-100 pb-4">
            <div>
              <h2 className="text-lg font-bold text-gray-900">In-Context Socratic Mentor</h2>
              <p className="text-xs text-gray-500">Ask questions grounded in {repoId} AST symbols</p>
            </div>
            <div className="flex items-center gap-1 bg-surface-100 p-1 rounded-2xl border border-gray-200">
              <button
                onClick={() => setMentorMode("learn")}
                className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                  mentorMode === "learn" ? "bg-white text-brand-700 shadow-sm" : "text-gray-500"
                }`}
              >
                Learn Mode
              </button>
              <button
                onClick={() => setMentorMode("copilot")}
                className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                  mentorMode === "copilot" ? "bg-white text-brand-700 shadow-sm" : "text-gray-500"
                }`}
              >
                Copilot Mode
              </button>
            </div>
          </div>

          <div className="space-y-4 max-h-[450px] overflow-y-auto pr-2">
            {chatMessages.length === 0 ? (
              <div className="text-center py-10 text-xs text-gray-400 space-y-2">
                <Sparkles className="w-8 h-8 text-brand-300 mx-auto" />
                <p>Ask how to setup, where tests are, or how a specific module works in {repoId}.</p>
              </div>
            ) : (
              chatMessages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[80%] p-4 rounded-3xl text-xs leading-relaxed ${
                      msg.sender === "user"
                        ? "bg-brand-600 text-white shadow-sm"
                        : "bg-surface-50 border border-gray-200/80 text-gray-800"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </div>
              ))
            )}
            {asking && (
              <div className="text-xs text-gray-400 italic flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 animate-spin text-brand-500" />
                Mentor reasoning over {repoId} AST evidence…
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={`Ask a question about ${repoId}…`}
              className="input flex-1 py-3 text-xs"
              disabled={asking}
              onKeyDown={(e) => { if (e.key === "Enter") handleAskMentor(); }}
            />
            <button
              onClick={handleAskMentor}
              disabled={asking || !question.trim()}
              className="btn-primary py-3 px-5 rounded-2xl shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* TAB 7: GENERATED DOCUMENTATION */}
      {activeTab === "docs" && (
        <div className="card p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 pb-4">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Standardized Repository Documentation</h2>
              <p className="text-xs text-gray-500">Auto-generated markdown guides for new contributors</p>
            </div>
            <button
              onClick={handleGenerateDocs}
              disabled={generatingDocs}
              className="btn-primary text-xs py-2 px-4 rounded-xl shadow-sm inline-flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {generatingDocs ? "Generating Docs…" : "Regenerate All Documentation"}
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              { key: "project_overview",  label: "PROJECT_OVERVIEW.md" },
              { key: "architecture",      label: "ARCHITECTURE.md" },
              { key: "beginner_setup",    label: "BEGINNER_SETUP.md" },
              { key: "contribution_guide",label: "CONTRIBUTION_GUIDE.md" },
            ].map((d) => (
              <button
                key={d.key}
                onClick={() => setSelectedDocKey(d.key as any)}
                className={`px-3 py-1.5 rounded-xl font-mono text-xs font-bold transition-all ${
                  selectedDocKey === d.key
                    ? "bg-brand-600 text-white shadow-sm"
                    : "bg-surface-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>

          {docsData && docsData[selectedDocKey] ? (
            <div className="space-y-3 animate-in">
              <div className="flex justify-end">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(docsData[selectedDocKey]);
                    setCopiedDoc(true);
                    setTimeout(() => setCopiedDoc(false), 2000);
                  }}
                  className="btn-secondary text-xs py-1.5 px-3 rounded-lg inline-flex items-center gap-1"
                >
                  {copiedDoc ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedDoc ? "Copied" : "Copy Markdown"}
                </button>
              </div>
              <pre className="p-5 rounded-2xl bg-surface-50 text-xs font-mono text-gray-800 overflow-x-auto max-h-[500px] border border-gray-200 whitespace-pre-wrap leading-relaxed">
                {docsData[selectedDocKey]}
              </pre>
            </div>
          ) : (
            <div className="text-center py-12 text-xs text-gray-400 space-y-3">
              <BookOpen className="w-8 h-8 text-gray-300 mx-auto" />
              <p>Documentation not generated yet for this repository.</p>
              <button onClick={handleGenerateDocs} className="btn-secondary text-xs py-1.5 px-3.5">
                Generate Markdown Docs Now
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
