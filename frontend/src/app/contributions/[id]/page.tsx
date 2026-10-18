"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { 
  getContribution, 
  updateStep, 
  runVerification, 
  analyzeDiff, 
  getContributionReport 
} from "@/lib/api";
import { 
  GitPullRequest, 
  CheckCircle2, 
  Circle, 
  Play, 
  Terminal, 
  ShieldCheck, 
  Copy, 
  Clock, 
  AlertTriangle, 
  FileCode, 
  Check, 
  ChevronRight,
  Sparkles,
  ArrowLeft
} from "lucide-react";

export default function ContributionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const { id } = resolvedParams;

  const [workspace, setWorkspace] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Verification Runner State
  const [testCmd, setTestCmd] = useState("pytest tests/ -v");
  const [runningTest, setRunningTest] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  // Diff Review State
  const [diffText, setDiffText] = useState("");
  const [reviewResult, setReviewResult] = useState<any>(null);
  const [reviewing, setReviewing] = useState(false);

  // PR Draft Modal / State
  const [prDraft, setPrDraft] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadWorkspace();
  }, [id]);

  const loadWorkspace = async () => {
    try {
      const data = await getContribution(id);
      setWorkspace(data);
    } catch {} finally {
      setLoading(false);
    }
  };

  const toggleStep = async (stepId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "completed" ? "pending" : "completed";
    try {
      await updateStep(id, stepId, nextStatus);
      loadWorkspace();
    } catch {}
  };

  const handleRunVerification = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testCmd.trim() || runningTest) return;

    setRunningTest(true);
    setTestResult(null);
    try {
      const res = await runVerification(testCmd, id, workspace?.repository_id);
      setTestResult(res);
      loadWorkspace();
    } catch (err: any) {
      setTestResult({
        status: "FAILED",
        exit_code: -1,
        stdout: "",
        stderr: err.message
      });
    } finally {
      setRunningTest(false);
    }
  };

  const handleAnalyzeDiff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!diffText.trim() || reviewing) return;

    setReviewing(true);
    try {
      const res = await analyzeDiff(diffText, id);
      setReviewResult(res);
      loadWorkspace();
    } catch {} finally {
      setReviewing(false);
    }
  };

  const handleGenerateReport = async () => {
    try {
      const res = await getContributionReport(id);
      setPrDraft(res);
    } catch {}
  };

  const handleCopyMarkdown = () => {
    if (prDraft?.markdown) {
      navigator.clipboard.writeText(prDraft.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-xs text-zinc-500 font-mono">Loading contribution workspace...</div>;
  }

  if (!workspace) {
    return <div className="p-12 text-center text-xs text-red-400">Workspace not found.</div>;
  }

  const completedSteps = workspace.steps?.filter((s: any) => s.status === "completed").length || 0;
  const totalSteps = workspace.steps?.length || 0;
  const progressPct = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header */}
      <div>
        <Link href="/contributions" className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1 mb-2 font-mono">
          <ArrowLeft className="h-3 w-3" /> Back to Workspaces
        </Link>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-mono text-xs text-emerald-400 font-semibold">{workspace.repository_id}</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {workspace.status}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-zinc-100">{workspace.title}</h1>
            <p className="text-xs text-zinc-400 mt-1 max-w-3xl">{workspace.description}</p>
          </div>

          <button
            onClick={handleGenerateReport}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer shrink-0"
          >
            <GitPullRequest className="h-3.5 w-3.5" />
            Generate PR Draft
          </button>
        </div>
      </div>

      {/* Progress Bar Header */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
        <div className="flex justify-between items-center text-xs">
          <span className="font-semibold text-zinc-300">Contribution Plan Execution</span>
          <span className="font-mono text-emerald-400">{completedSteps} of {totalSteps} steps completed ({progressPct}%)</span>
        </div>
        <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
          <div
            className="bg-emerald-500 h-full rounded-full transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Step Checklist (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              Actionable Contribution Steps
            </h2>

            <div className="space-y-3">
              {workspace.steps?.map((step: any) => {
                const isDone = step.status === "completed";
                return (
                  <div
                    key={step.id}
                    onClick={() => toggleStep(step.id, step.status)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer flex items-start gap-3.5 ${
                      isDone
                        ? "bg-emerald-950/20 border-emerald-500/30 text-zinc-300"
                        : "bg-zinc-950/70 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    <div className="mt-0.5 shrink-0">
                      {isDone ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <Circle className="h-5 w-5 text-zinc-600" />
                      )}
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-semibold ${isDone ? "text-emerald-300 line-through" : "text-zinc-200"}`}>
                          {step.title}
                        </span>
                        <span className="text-[10px] font-mono text-zinc-500 uppercase">{step.status}</span>
                      </div>
                      <p className="text-xs text-zinc-400 leading-relaxed">{step.description}</p>
                      {step.expected_result && (
                        <p className="text-[11px] text-zinc-500 font-mono">
                          Expected result: {step.expected_result}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Safe Verification Runner */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <Terminal className="h-4 w-4 text-cyan-400" />
                Pre-Flight Verification Runner
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Executes unit tests in a safe, sandboxed subprocess. Captures truthful stdout/stderr and exit codes.
              </p>
            </div>

            <form onSubmit={handleRunVerification} className="flex gap-2">
              <input
                type="text"
                placeholder="Verification command (e.g. pytest tests/ -v or python -m unittest)..."
                value={testCmd}
                onChange={(e) => setTestCmd(e.target.value)}
                className="flex-1 p-2.5 rounded-lg border border-zinc-800 bg-zinc-950 font-mono text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
                disabled={runningTest}
              />
              <button
                type="submit"
                disabled={runningTest || !testCmd.trim()}
                className="px-4 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 shrink-0"
              >
                {runningTest ? (
                  <>
                    <span className="h-3 w-3 border-2 border-zinc-950 border-t-transparent rounded-full animate-spin"></span>
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="h-3.5 w-3.5" /> Run Test
                  </>
                )}
              </button>
            </form>

            {testResult && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono font-bold text-zinc-300">Exit Code: {testResult.exit_code}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    testResult.status === "PASSED" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
                  }`}>
                    {testResult.status} ({testResult.duration_ms}ms)
                  </span>
                </div>

                {testResult.stdout && (
                  <div>
                    <span className="text-[10px] font-mono text-zinc-500 block">STDOUT:</span>
                    <pre className="p-2 rounded bg-zinc-900 text-[11px] font-mono text-zinc-300 overflow-x-auto max-h-40">
                      {testResult.stdout}
                    </pre>
                  </div>
                )}

                {testResult.stderr && (
                  <div>
                    <span className="text-[10px] font-mono text-zinc-500 block">STDERR:</span>
                    <pre className="p-2 rounded bg-zinc-900 text-[11px] font-mono text-red-400 overflow-x-auto max-h-40">
                      {testResult.stderr}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* PR Review Simulator */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-amber-400" />
                PR Review Simulator
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Paste your git diff to catch leaked secrets, debug statements, silent exception suppression, and missing tests before maintainers see it.
              </p>
            </div>

            <form onSubmit={handleAnalyzeDiff} className="space-y-3">
              <textarea
                rows={5}
                placeholder="Paste unified git diff here (e.g. diff --git a/file.py b/file.py)..."
                value={diffText}
                onChange={(e) => setDiffText(e.target.value)}
                className="w-full p-3 rounded-lg border border-zinc-800 bg-zinc-950 font-mono text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
              />
              <button
                type="submit"
                disabled={reviewing || !diffText.trim()}
                className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 font-semibold text-xs transition-colors cursor-pointer disabled:opacity-50"
              >
                {reviewing ? "Analyzing Diff..." : "Simulate Maintainer Review"}
              </button>
            </form>

            {reviewResult && (
              <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-950 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-zinc-200">Review Status:</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-400">
                    {reviewResult.overall_status}
                  </span>
                </div>

                {reviewResult.findings?.length > 0 ? (
                  <div className="space-y-2">
                    {reviewResult.findings.map((f: any) => (
                      <div key={f.id} className="p-2.5 rounded bg-zinc-900 border border-zinc-800 text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-amber-400 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" /> {f.title}
                          </span>
                          <span className="font-mono text-[10px] uppercase text-zinc-500">{f.severity}</span>
                        </div>
                        <p className="text-zinc-400 text-[11px]">{f.explanation}</p>
                        <p className="text-emerald-400 text-[11px] font-mono">Suggested fix: {f.suggested_fix}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-emerald-400">✅ Clean diff. No secrets or debug statements detected.</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Flight Recorder Timeline (1 col) */}
        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <Clock className="h-4 w-4 text-emerald-400" />
              Flight Recorder Audit Trail
            </h2>
            <p className="text-[11px] text-zinc-400">
              Immutable log of every action taken from exploration to verification.
            </p>

            <div className="relative border-l border-zinc-800 ml-2 pl-4 space-y-4">
              {workspace.timeline?.map((event: any) => (
                <div key={event.id} className="relative group">
                  <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-emerald-500 border border-zinc-950" />
                  <div className="text-[10px] font-mono text-zinc-500 uppercase">{event.event_type}</div>
                  <div className="text-xs font-semibold text-zinc-300 mt-0.5">{event.summary}</div>
                  {event.details && (
                    <div className="text-[11px] text-zinc-500 mt-1 whitespace-pre-wrap font-mono line-clamp-3">
                      {event.details}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Generated PR Draft Modal / View */}
      {prDraft && (
        <div className="rounded-2xl border border-emerald-500/30 bg-zinc-900/90 p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div>
              <span className="text-[10px] font-mono uppercase text-emerald-400 block">Flight Recorder Verified</span>
              <h3 className="text-base font-bold text-zinc-100">{prDraft.title}</h3>
            </div>
            <button
              onClick={handleCopyMarkdown}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer"
            >
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "Copied!" : "Copy PR Markdown"}
            </button>
          </div>

          <pre className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs text-zinc-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
            {prDraft.markdown}
          </pre>
        </div>
      )}
    </div>
  );
}
