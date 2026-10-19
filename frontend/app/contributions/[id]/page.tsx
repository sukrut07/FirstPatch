"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getContribution,
  updateStep,
  runVerification,
  analyzeDiff,
  getContributionReport,
} from "@/lib/api";
import {
  GitPullRequest,
  CheckCircle2,
  Clock,
  Play,
  Terminal,
  ShieldCheck,
  FileCode,
  Download,
  Copy,
  Check,
  ArrowRight,
  AlertCircle,
  Sparkles,
  Layers,
} from "lucide-react";

export default function ContributionWorkspacePage({
  params,
}: {
  params: { id: string };
}) {
  const contributionId = params.id;

  const [contribution, setContribution] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Verification Sandbox State
  const [testCommand, setTestCommand] = useState("pytest tests/");
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<any>(null);

  // Review Simulation State
  const [diffInput, setDiffInput] = useState(
    "diff --git a/app/main.py b/app/main.py\nindex 1234567..89abcdef 100644\n--- a/app/main.py\n+++ b/app/main.py\n@@ -10,4 +10,6 @@ def run_app():\n-    pass\n+    # Fixed configuration lookup bug\n+    timeout = settings.get('TIMEOUT', 30)\n+    return timeout"
  );
  const [reviewing, setReviewing] = useState(false);
  const [reviewResult, setReviewResult] = useState<any>(null);

  // Export State
  const [report, setReport] = useState<any>(null);
  const [copiedDraft, setCopiedDraft] = useState(false);

  useEffect(() => {
    loadWorkspace();
  }, [contributionId]);

  const loadWorkspace = async () => {
    setLoading(true);
    try {
      const data = await getContribution(contributionId);
      setContribution(data);
    } catch (err: any) {
      setError(err.message || "Failed to load contribution workspace.");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStep = async (step: any) => {
    const nextStatus = step.status === "completed" ? "todo" : "completed";
    try {
      await updateStep(contributionId, step.id, nextStatus);
      setContribution((prev: any) => {
        if (!prev) return prev;
        const updatedSteps = (prev.steps || []).map((s: any) =>
          s.id === step.id ? { ...s, status: nextStatus } : s
        );
        return { ...prev, steps: updatedSteps };
      });
    } catch (e: any) {
      alert("Failed to update step status: " + e.message);
    }
  };

  const handleRunVerification = async () => {
    if (!testCommand.trim()) return;
    setVerifying(true);
    setVerificationResult(null);
    try {
      const res = await runVerification(
        testCommand.trim(),
        contributionId,
        contribution?.repository_id
      );
      setVerificationResult(res);
    } catch (err: any) {
      setVerificationResult({
        status: "error",
        output: err.message || "Execution failed",
        exit_code: 1,
      });
    } finally {
      setVerifying(false);
    }
  };

  const handleSimulateReview = async () => {
    if (!diffInput.trim()) return;
    setReviewing(true);
    setReviewResult(null);
    try {
      const res = await analyzeDiff(diffInput.trim(), contributionId);
      setReviewResult(res);
    } catch (err: any) {
      setReviewResult({
        status: "error",
        feedback: err.message || "Review analysis failed",
        score: 0,
      });
    } finally {
      setReviewing(false);
    }
  };

  const handleExportReport = async () => {
    try {
      const rep = await getContributionReport(contributionId);
      setReport(rep);
    } catch (err: any) {
      alert("Failed to export report: " + err.message);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 space-y-4">
        <div className="card p-8 skeleton h-64" />
      </div>
    );
  }

  if (error || !contribution) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <div className="card p-8 space-y-4">
          <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-gray-900">Workspace Not Found</h2>
          <p className="text-xs text-gray-500">{error || "Could not retrieve workspace."}</p>
          <Link href="/contributions" className="btn-secondary text-xs inline-flex items-center gap-1.5">
            Back to Flight Recorder
          </Link>
        </div>
      </div>
    );
  }

  const steps = contribution.steps || [
    { id: "1", title: "Problem Restatement & Triage", status: "completed", order: 1 },
    { id: "2", title: "Isolate Failing Test Case", status: "completed", order: 2 },
    { id: "3", title: "Implement AST Scoped Fix", status: "in_progress", order: 3 },
    { id: "4", title: "Verification Sandbox & Review Simulation", status: "todo", order: 4 },
  ];

  const completedSteps = steps.filter((s: any) => s.status === "completed").length;
  const progressPct = Math.round((completedSteps / steps.length) * 100);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Top Banner */}
      <div className="card-brand flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link href="/contributions" className="text-xs font-bold text-brand-600 hover:text-brand-800">
              &larr; Flight Recorder
            </Link>
            <span className="text-gray-300">&bull;</span>
            <span className="badge-brand font-mono text-[10px]">{contribution.repository_id}</span>
          </div>
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">{contribution.title}</h1>
          <p className="text-xs text-gray-500 leading-relaxed max-w-2xl">{contribution.description || "Grounded contribution journey."}</p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleExportReport}
            className="btn-secondary text-xs py-2 px-3.5 rounded-xl shadow-sm inline-flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" /> Export Audit Ledger
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="card p-5 space-y-2">
        <div className="flex justify-between text-xs font-bold text-gray-700">
          <span>Contribution Progress ({completedSteps}/{steps.length} Steps)</span>
          <span className="text-brand-600 font-mono">{progressPct}%</span>
        </div>
        <div className="score-bar">
          <div
            className="score-fill bg-gradient-to-r from-brand-500 via-purple-500 to-emerald-500"
            style={{ width: `${Math.max(progressPct, 15)}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: 4-Phase Checklist */}
        <div className="space-y-6">
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h2 className="text-sm font-bold text-gray-900">4-Phase Contribution Checklist</h2>
              <span className="text-[10px] font-bold text-brand-600 uppercase tracking-wider">Click to Toggle</span>
            </div>

            <div className="space-y-3">
              {steps.map((step: any) => {
                const isDone = step.status === "completed";
                return (
                  <div
                    key={step.id}
                    onClick={() => handleToggleStep(step)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-start gap-3.5 ${
                      isDone
                        ? "bg-emerald-50/50 border-emerald-200/80 shadow-sm"
                        : "bg-white border-gray-200/80 hover:border-brand-200 shadow-sm"
                    }`}
                  >
                    <div
                      className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs ${
                        isDone
                          ? "bg-emerald-500 text-white"
                          : "border-2 border-gray-300 text-transparent"
                      }`}
                    >
                      ✓
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs font-bold ${isDone ? "text-emerald-900 line-through" : "text-gray-900"}`}>
                        {step.title || step.description}
                      </p>
                      {step.rationale && (
                        <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">{step.rationale}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Exported Report Display */}
          {report && (
            <div className="card p-6 space-y-3 animate-in">
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                Flight Recorder Audit Report
              </h3>
              <pre className="p-3 rounded-xl bg-surface-100 text-[11px] font-mono text-gray-800 overflow-x-auto max-h-60 border border-gray-200">
                {JSON.stringify(report, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Right Column: Verification Sandbox & Review Simulator */}
        <div className="space-y-6">
          {/* Tool 1: Verification Sandbox */}
          <div className="card p-6 space-y-4">
            <div className="flex items-center gap-2 text-brand-700">
              <Terminal className="w-4 h-4" />
              <h3 className="text-sm font-bold text-gray-900">Automated Verification Sandbox</h3>
            </div>
            <p className="text-xs text-gray-500">
              Execute test commands in restricted subprocesses to verify your reproduction or bugfix.
            </p>

            <div className="flex gap-2">
              <input
                type="text"
                value={testCommand}
                onChange={(e) => setTestCommand(e.target.value)}
                placeholder="pytest tests/test_main.py"
                className="input py-2 text-xs font-mono flex-1"
                disabled={verifying}
              />
              <button
                onClick={handleRunVerification}
                disabled={verifying || !testCommand.trim()}
                className="btn-primary text-xs py-2 px-4 rounded-xl shrink-0"
              >
                {verifying ? "Executing…" : "Run Test"}
              </button>
            </div>

            {verificationResult && (
              <div className="p-4 rounded-2xl bg-surface-100 border border-gray-200 space-y-2 animate-in">
                <div className="flex items-center justify-between text-xs">
                  <span className={`badge font-bold ${verificationResult.status === "completed" || verificationResult.status === "PASSED" ? "badge-success" : "badge-error"}`}>
                    {verificationResult.status || (verificationResult.exit_code === 0 ? "PASSED" : "FAILED")}
                  </span>
                  <span className="font-mono text-[10px] text-gray-500">
                    Exit Code: {verificationResult.exit_code ?? 0}
                  </span>
                </div>
                <pre className="text-[11px] font-mono text-gray-800 bg-white p-3 rounded-xl border border-gray-200/80 max-h-40 overflow-y-auto whitespace-pre-wrap">
                  {verificationResult.output || verificationResult.stdout || "Command executed with no output."}
                </pre>
              </div>
            )}
          </div>

          {/* Tool 2: PR Diff Review Simulator */}
          <div className="card p-6 space-y-4">
            <div className="flex items-center gap-2 text-purple-700">
              <ShieldCheck className="w-4 h-4" />
              <h3 className="text-sm font-bold text-gray-900">PR Diff Review Simulator</h3>
            </div>
            <p className="text-xs text-gray-500">
              Simulate maintainer review before submitting: check for secret leaks, style conventions, and receive constructive feedback.
            </p>

            <textarea
              rows={4}
              value={diffInput}
              onChange={(e) => setDiffInput(e.target.value)}
              placeholder="Paste git diff here..."
              className="input text-xs font-mono py-2"
              disabled={reviewing}
            />

            <button
              onClick={handleSimulateReview}
              disabled={reviewing || !diffInput.trim()}
              className="btn-secondary text-xs py-2 px-4 rounded-xl w-full justify-center font-bold text-brand-700"
            >
              {reviewing ? "Simulating Review…" : "Run Review Simulation"}
            </button>

            {reviewResult && (
              <div className="p-4 rounded-2xl bg-purple-50/60 border border-purple-200 space-y-2 animate-in text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-purple-900">Maintainer Review Score</span>
                  <span className="font-mono font-extrabold text-sm text-brand-700">
                    {reviewResult.score ?? 95}/100
                  </span>
                </div>
                <p className="text-gray-700 leading-relaxed bg-white p-3 rounded-xl border border-purple-100">
                  {reviewResult.feedback || "Diff looks clean and ready for contribution review."}
                </p>
                {reviewResult.leaks_detected && reviewResult.leaks_detected.length > 0 && (
                  <p className="text-rose-600 font-bold">
                    ⚠️ Potential secrets detected: {reviewResult.leaks_detected.join(", ")}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
