"use client";

import React, { useState, useEffect } from "react";
import {
  api,
  type VerificationInfrastructureHealth,
  type VerificationRunRecord,
  type RuntimeProfile,
  type RepositoryOverview,
  type ContributionPlan,
} from "@/lib/api";
import { IconSpinner, IconWarning, IconInfo } from "@/components/ui";

interface VerificationPanelProps {
  repo: RepositoryOverview;
  plan?: ContributionPlan | null;
}

export function VerificationPanel({ repo, plan }: VerificationPanelProps) {
  const [health, setHealth] = useState<VerificationInfrastructureHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [selectedRuntime, setSelectedRuntime] = useState<RuntimeProfile>("python_pytest");
  const [testTarget, setTestTarget] = useState<string>("tests");
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<VerificationRunRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(false);

  // Auto-detect default runtime based on primary language
  useEffect(() => {
    if (repo.primary_language?.toLowerCase().includes("python")) {
      setSelectedRuntime("python_pytest");
      setTestTarget("tests");
    } else if (
      repo.primary_language?.toLowerCase().includes("javascript") ||
      repo.primary_language?.toLowerCase().includes("typescript")
    ) {
      setSelectedRuntime("node_jest");
      setTestTarget("__tests__");
    }
  }, [repo.primary_language]);

  // Load infrastructure health on mount
  useEffect(() => {
    let mounted = true;
    async function fetchHealth() {
      try {
        const data = await api.getVerificationHealth();
        if (mounted) {
          setHealth(data);
          setHealthLoading(false);
        }
      } catch {
        if (mounted) {
          setHealthLoading(false);
        }
      }
    }
    fetchHealth();
    return () => {
      mounted = false;
    };
  }, []);

  async function handleTriggerRun() {
    if (!repo.commit_sha) {
      setError("Repository snapshot commit SHA is required for verifiable test execution.");
      return;
    }
    setError(null);
    setIsRunning(true);
    setShowLogs(false);

    try {
      const record = await api.submitVerificationRun({
        owner: repo.identity.owner,
        repo: repo.identity.repo,
        commit_sha: repo.commit_sha,
        runtime: selectedRuntime,
        test_target: testTarget,
        timeout_seconds: 45,
        session_id: plan?.session_id,
      });
      setCurrentRun(record);

      // If run was immediately queued/running, poll briefly for resolution
      if (record.status === "queued" || record.status === "preparing" || record.status === "running") {
        pollRun(record.run_id);
      } else {
        setIsRunning(false);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit verification run.");
      setIsRunning(false);
    }
  }

  async function pollRun(runId: string) {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const updated = await api.getVerificationRun(runId);
        setCurrentRun(updated);
        if (
          updated.status !== "queued" &&
          updated.status !== "preparing" &&
          updated.status !== "running"
        ) {
          clearInterval(interval);
          setIsRunning(false);
        }
      } catch {
        // Stop polling on error
        clearInterval(interval);
        setIsRunning(false);
      }
      if (attempts >= 30) {
        clearInterval(interval);
        setIsRunning(false);
      }
    }, 1500);
  }

  const commitShort = repo.commit_sha ? repo.commit_sha.substring(0, 8) : "unpinned";

  return (
    <div className="card space-y-5 border border-white/[0.08]" id="verification-panel">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-white">Isolated Test Verification</h3>
            <span className="badge badge-neutral text-xs font-mono">Phase 3</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Safely execute repository tests inside hardened containers. No unverified claims.
          </p>
        </div>

        {/* Snapshot commitment badge */}
        <div className="flex items-center gap-2 self-start sm:self-auto text-xs font-mono bg-surface-900 border border-white/[0.08] px-2.5 py-1.5 rounded-md">
          <span className="text-gray-500">Snapshot Commit:</span>
          <span className="text-brand-300 font-semibold">{commitShort}</span>
        </div>
      </div>

      {/* Discovery vs Execution Distinction */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
        <div className="bg-surface-900/60 p-3 rounded-lg border border-white/[0.04]">
          <span className="text-gray-400 block font-medium mb-1">Discovered Test Suites</span>
          {repo.test_locations.length > 0 ? (
            <ul className="space-y-1 text-gray-300">
              {repo.test_locations.map((loc, i) => (
                <li key={i} className="flex items-center gap-1.5 font-mono text-2xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400/80 shrink-0" />
                  <span className="truncate">{loc.path}</span>
                  {loc.framework && (
                    <span className="text-gray-500">({loc.framework})</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <span className="text-gray-500 italic">No automated tests recognized in snapshot.</span>
          )}
        </div>

        <div className="bg-surface-900/60 p-3 rounded-lg border border-white/[0.04]">
          <span className="text-gray-400 block font-medium mb-1">Sandbox Infrastructure</span>
          {healthLoading ? (
            <div className="flex items-center gap-1.5 text-gray-500">
              <IconSpinner className="w-3.5 h-3.5 animate-spin" />
              <span>Probing sandbox runtime...</span>
            </div>
          ) : health?.runtime_available ? (
            <div className="text-status-success flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-status-success animate-pulse" />
              <span>Container sandbox active ({health.runtime_name})</span>
            </div>
          ) : (
            <div className="text-status-warning flex items-start gap-1.5">
              <IconWarning className="w-4 h-4 shrink-0 text-status-warning mt-0.5" />
              <div>
                <span className="font-semibold block">Sandbox Unavailable</span>
                <span className="text-gray-400 text-2xs leading-relaxed">
                  {health?.message || "Container engine not detected. Host execution is strictly disabled."}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Execution Control Form */}
      <div className="bg-surface-900/80 p-4 rounded-lg border border-white/[0.06] space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Runtime Profile
            </label>
            <select
              value={selectedRuntime}
              onChange={(e) => setSelectedRuntime(e.target.value as RuntimeProfile)}
              disabled={isRunning}
              className="w-full bg-surface-800 border border-white/[0.08] rounded-md px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-brand-500"
            >
              <option value="python_pytest">Python: pytest (preconfigured 3.11)</option>
              <option value="node_jest">Node.js: jest (preconfigured 20-slim)</option>
              <option value="node_npm_test">Node.js: npm test</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Allowlisted Test Target
            </label>
            <input
              type="text"
              value={testTarget}
              onChange={(e) => setTestTarget(e.target.value)}
              disabled={isRunning}
              placeholder="e.g. tests or tests/test_core.py"
              className="w-full bg-surface-800 border border-white/[0.08] rounded-md px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-brand-500 font-mono"
            />
          </div>
        </div>

        {error && (
          <div className="text-xs text-status-error bg-status-error/10 border border-status-error/20 p-2.5 rounded-md">
            {error}
          </div>
        )}

        <div className="flex items-center justify-between pt-1">
          <p className="text-2xs text-gray-500 flex items-center gap-1">
            <IconInfo className="w-3.5 h-3.5 shrink-0" />
            <span>Network disabled &bull; Read-only source &bull; 50KB bounded logs</span>
          </p>

          <button
            onClick={handleTriggerRun}
            disabled={isRunning || !repo.commit_sha}
            className="btn btn-primary text-xs py-2 px-4 font-semibold flex items-center gap-2"
            id="run-verification-btn"
          >
            {isRunning ? (
              <>
                <IconSpinner className="w-3.5 h-3.5 animate-spin" />
                <span>Running Isolated Verification...</span>
              </>
            ) : (
              <span>Run Tests in Sandbox</span>
            )}
          </button>
        </div>
      </div>

      {/* Verification Result Section */}
      {currentRun && (
        <div
          className={`p-4 rounded-lg border text-xs space-y-3 ${
            currentRun.status === "passed"
              ? "bg-status-success/5 border-status-success/30"
              : currentRun.status === "failed"
              ? "bg-status-error/5 border-status-error/30"
              : currentRun.status === "unavailable"
              ? "bg-surface-800/80 border-white/[0.08]"
              : "bg-surface-900 border-white/[0.06]"
          }`}
          id="verification-result-card"
        >
          {/* Status badge and run identity */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className={`font-semibold uppercase tracking-wider text-2xs px-2 py-0.5 rounded ${
                  currentRun.status === "passed"
                    ? "bg-status-success/20 text-status-success"
                    : currentRun.status === "failed"
                    ? "bg-status-error/20 text-status-error"
                    : currentRun.status === "timed_out"
                    ? "bg-status-warning/20 text-status-warning"
                    : currentRun.status === "unavailable"
                    ? "bg-gray-700 text-gray-300"
                    : "bg-brand-500/20 text-brand-300"
                }`}
              >
                {currentRun.status.replace("_", " ")}
              </span>
              <span className="text-gray-400 font-mono text-2xs">
                Run: {currentRun.run_id.substring(0, 8)}
              </span>
            </div>

            {currentRun.duration_ms && (
              <span className="text-gray-500 text-2xs">
                {(currentRun.duration_ms / 1000).toFixed(2)}s elapsed
              </span>
            )}
          </div>

          {/* Test Statistics Summary */}
          {currentRun.counts && (
            <div className="grid grid-cols-4 gap-2 text-center py-2 bg-surface-950/60 rounded border border-white/[0.04] font-mono">
              <div>
                <span className="text-2xs text-gray-500 block">Collected</span>
                <span className="text-sm font-bold text-gray-200">{currentRun.counts.collected}</span>
              </div>
              <div>
                <span className="text-2xs text-gray-500 block">Passed</span>
                <span className="text-sm font-bold text-status-success">{currentRun.counts.passed}</span>
              </div>
              <div>
                <span className="text-2xs text-gray-500 block">Failed</span>
                <span className={`text-sm font-bold ${currentRun.counts.failed > 0 ? "text-status-error" : "text-gray-400"}`}>
                  {currentRun.counts.failed}
                </span>
              </div>
              <div>
                <span className="text-2xs text-gray-500 block">Errors</span>
                <span className={`text-sm font-bold ${currentRun.counts.errors > 0 ? "text-status-error" : "text-gray-400"}`}>
                  {currentRun.counts.errors}
                </span>
              </div>
            </div>
          )}

          {/* Error Summary Note */}
          {currentRun.error_summary && (
            <div className="text-xs text-gray-300 font-mono bg-surface-950/90 p-2.5 rounded border border-white/[0.05] whitespace-pre-wrap max-h-40 overflow-y-auto">
              {currentRun.error_summary}
            </div>
          )}

          {/* Warnings */}
          {currentRun.warnings.length > 0 && (
            <div className="space-y-1">
              {currentRun.warnings.map((w, i) => (
                <p key={i} className="text-2xs text-status-warning flex items-center gap-1.5">
                  <IconWarning className="w-3.5 h-3.5 shrink-0" />
                  <span>{w}</span>
                </p>
              ))}
            </div>
          )}

          {/* Toggle raw stdout/stderr logs */}
          {(currentRun.stdout || currentRun.stderr) && (
            <div className="pt-1">
              <button
                onClick={() => setShowLogs(!showLogs)}
                className="text-2xs text-brand-400 hover:text-brand-300 underline font-medium"
              >
                {showLogs ? "Hide Bounded Execution Output" : "View Bounded Execution Output (50KB max)"}
              </button>

              {showLogs && (
                <div className="mt-2 text-2xs font-mono bg-surface-950 p-3 rounded border border-white/[0.08] max-h-60 overflow-y-auto whitespace-pre-wrap text-gray-300">
                  {currentRun.stdout && (
                    <div>
                      <span className="text-gray-500 font-bold block mb-1">--- STDOUT ---</span>
                      {currentRun.stdout}
                    </div>
                  )}
                  {currentRun.stderr && (
                    <div className="mt-2 text-status-error/90">
                      <span className="text-status-error font-bold block mb-1">--- STDERR ---</span>
                      {currentRun.stderr}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
