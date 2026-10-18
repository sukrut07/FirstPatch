"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  getIssueInvestigation, 
  getIssueTriage, 
  saveIssueTriage, 
  addIssueHypothesis, 
  updateIssueHypothesisStatus, 
  getMaintainerDrafts,
  planContribution,
  createContribution
} from "@/lib/api";
import { 
  Compass, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  ExternalLink, 
  Sparkles, 
  FileCode2, 
  Layers, 
  ArrowRight, 
  Copy, 
  Check, 
  HelpCircle, 
  MessageSquare, 
  Plus, 
  Terminal, 
  XCircle,
  Network
} from "lucide-react";

export default function IssueInvestigationPage({
  params,
}: {
  params: Promise<{ owner: string; repo: string; number: string }>;
}) {
  const resolvedParams = use(params);
  const { owner, repo, number } = resolvedParams;
  const issueNumber = parseInt(number, 10);
  const repoId = `${owner}/${repo}`;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<"investigation" | "triage" | "drafts">("investigation");
  const [data, setData] = useState<any>(null);
  const [triage, setTriage] = useState<any>({
    user_summary: "",
    expected_behavior: "",
    actual_behavior: "",
    suspected_code_path: "",
    reproduction_notes: "",
    decision: "undecided",
    decision_rationale: ""
  });
  const [hypotheses, setHypotheses] = useState<any[]>([]);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // New Hypothesis Form
  const [newHypothesis, setNewHypothesis] = useState("");
  const [newEvidence, setNewEvidence] = useState("");
  const [addingHypo, setAddingHypo] = useState(false);

  // Action states
  const [savingTriage, setSavingTriage] = useState(false);
  const [copiedDraft, setCopiedDraft] = useState<string | null>(null);
  const [planning, setPlanning] = useState(false);

  useEffect(() => {
    loadAllData();
  }, [owner, repo, issueNumber]);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [invRes, triageRes, draftsRes] = await Promise.all([
        getIssueInvestigation(owner, repo, issueNumber),
        getIssueTriage(owner, repo, issueNumber),
        getMaintainerDrafts(owner, repo, issueNumber)
      ]);
      setData(invRes);
      if (triageRes?.triage) setTriage(triageRes.triage);
      if (triageRes?.hypotheses) setHypotheses(triageRes.hypotheses);
      if (draftsRes?.drafts) setDrafts(draftsRes.drafts);
    } catch (e: any) {
      console.error("Failed to load investigation data:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveTriage = async (customDecision?: string) => {
    setSavingTriage(true);
    const updatedTriage = {
      ...triage,
      decision: customDecision || triage.decision
    };
    try {
      await saveIssueTriage(owner, repo, issueNumber, updatedTriage);
      setTriage(updatedTriage);
    } catch (e: any) {
      alert("Failed to save triage notes: " + e.message);
    } finally {
      setSavingTriage(false);
    }
  };

  const handleAddHypothesis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHypothesis.trim()) return;
    setAddingHypo(true);
    try {
      const evidenceList = newEvidence.trim() ? [newEvidence.trim()] : [];
      await addIssueHypothesis(owner, repo, issueNumber, {
        hypothesis: newHypothesis.trim(),
        supporting_evidence: evidenceList,
        status: "untested"
      });
      setNewHypothesis("");
      setNewEvidence("");
      const updated = await getIssueTriage(owner, repo, issueNumber);
      if (updated?.hypotheses) setHypotheses(updated.hypotheses);
    } catch (e: any) {
      alert("Failed to add hypothesis: " + e.message);
    } finally {
      setAddingHypo(false);
    }
  };

  const handleUpdateHypoStatus = async (hypoId: string, status: string) => {
    try {
      await updateIssueHypothesisStatus(owner, repo, issueNumber, hypoId, status);
      const updated = await getIssueTriage(owner, repo, issueNumber);
      if (updated?.hypotheses) setHypotheses(updated.hypotheses);
    } catch (e: any) {
      alert("Failed to update status: " + e.message);
    }
  };

  const handleCopyDraft = (draftType: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedDraft(draftType);
    setTimeout(() => setCopiedDraft(null), 2000);
  };

  const handleProceedToPlan = async () => {
    setPlanning(true);
    try {
      await handleSaveTriage("proceed");
      const planRes = await planContribution({
        repositoryId: repoId,
        issueTitle: data.issue.title,
        issueDescription: data.issue.body,
        issueId: data.issue.id
      });
      const ws = await createContribution({
        repositoryId: repoId,
        issueId: data.issue.id,
        title: data.issue.title,
        description: data.issue.body,
        steps: planRes.plan?.step_by_step_plan
      });
      router.push(`/contributions/${ws.workspace_id}`);
    } catch (e: any) {
      alert("Failed to proceed: " + e.message);
    } finally {
      setPlanning(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <span className="h-7 w-7 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></span>
        <p className="text-xs text-zinc-400 font-mono">
          Correlating issue #{issueNumber} with repository AST snapshot...
        </p>
      </div>
    );
  }

  const { issue, recommendation: rec, investigation: inv } = data;
  const claimSafety = rec?.claim_safety || { status: "ACTIONABLE_SIGNAL_FOUND", is_safe_to_claim: true, reason: "Open for contribution." };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between text-xs text-zinc-400">
        <div className="flex items-center gap-1.5 font-mono">
          <Link href={`/repo/${owner}/${repo}`} className="hover:text-emerald-400 transition-colors">
            {repoId}
          </Link>
          <span>/</span>
          <span>issues</span>
          <span>/</span>
          <span className="text-zinc-200">#{issueNumber}</span>
        </div>
        <Link
          href={`/repo/${owner}/${repo}`}
          className="hover:text-zinc-200 transition-colors flex items-center gap-1"
        >
          ← Back to Repository Explorer
        </Link>
      </div>

      {/* Issue Header Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-mono text-zinc-500">#{issue.number}</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {rec?.category || "Bug"}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-400 border border-zinc-700">
                Complexity: {rec?.estimated_complexity || "Beginner"}
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold flex items-center gap-1 ${
                claimSafety.is_safe_to_claim 
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                  : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
              }`}>
                {claimSafety.is_safe_to_claim ? <CheckCircle2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                {claimSafety.status}
              </span>
            </div>

            <h1 className="text-xl sm:text-2xl font-bold text-zinc-100">{issue.title}</h1>
            <p className="text-xs text-zinc-400 flex items-center gap-3 font-mono">
              <span>Opened by @{issue.author || "contributor"}</span>
              <span>•</span>
              <a href={issue.html_url} target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline flex items-center gap-1">
                View on GitHub <ExternalLink className="h-3 w-3" />
              </a>
            </p>
          </div>

          {/* Quick Fit Summary */}
          <div className="flex items-center gap-4 bg-zinc-950/80 p-3.5 rounded-xl border border-zinc-800 shrink-0">
            <div className="text-center">
              <div className="text-2xl font-extrabold text-emerald-400 font-mono">{rec?.fit_score}%</div>
              <div className="text-[10px] uppercase font-mono text-zinc-500">Overall Fit</div>
            </div>
            <div className="h-8 w-px bg-zinc-800" />
            <div className="text-xs space-y-1">
              <div className="text-zinc-300 font-medium">Effort: <span className="text-zinc-400">{rec?.estimated_effort || "1-2 hours"}</span></div>
              <div className="text-zinc-300 font-medium">Evidence: <span className="text-emerald-400 font-mono">{rec?.confidence || "High"}</span></div>
            </div>
          </div>
        </div>

        {/* Claim Safety Warning / Advisory */}
        {!claimSafety.is_safe_to_claim && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-400" />
            <div>
              <strong>Claim-Safety Advisory:</strong> {claimSafety.reason}
              <div className="mt-1 text-[11px] text-amber-400/80">
                Recommendation: Use the <strong>Maintainer Drafts</strong> tab to ask before spending time implementing.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-2 border-b border-zinc-800 pb-2">
        <button
          onClick={() => setActiveTab("investigation")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === "investigation"
              ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <Compass className="h-3.5 w-3.5 text-emerald-400" />
          1. Grounded Investigation & Code Map
        </button>

        <button
          onClick={() => setActiveTab("triage")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === "triage"
              ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <FileCode2 className="h-3.5 w-3.5 text-cyan-400" />
          2. Contributor Triage & Hypotheses
          {hypotheses.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-zinc-700 text-zinc-300">
              {hypotheses.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("drafts")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === "drafts"
              ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <MessageSquare className="h-3.5 w-3.5 text-purple-400" />
          3. Maintainer Communication Drafts ({drafts.length})
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: GROUNDED INVESTIGATION */}
      {/* ========================================================================= */}
      {activeTab === "investigation" && (
        <div className="space-y-6">
          {/* Multidimensional Fit Score Matrix */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-zinc-400">
              Multidimensional Recommendation Evaluation
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {[
                { label: "Technical Fit", score: rec?.technical_fit_score || 70, desc: "Code complexity vs. beginner skills" },
                { label: "Interest Fit", score: rec?.interest_fit_score || 80, desc: "Matches your preferred tech stack" },
                { label: "Evidence Confidence", score: rec?.evidence_confidence_score || 75, desc: "Stack trace & symbol match strength" },
                { label: "Contribution Viability", score: rec?.viability_score || 85, desc: "Absence of blockers / unassigned" },
                { label: "Learning Value", score: rec?.learning_value_score || 80, desc: "Yield of mastering this concept" },
              ].map((dim) => (
                <div key={dim.label} className="bg-zinc-950 p-3 rounded-lg border border-zinc-800/80 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-zinc-400 font-medium">{dim.label}</span>
                    <strong className="font-mono text-emerald-400">{dim.score}%</strong>
                  </div>
                  <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${dim.score}%` }} />
                  </div>
                  <p className="text-[10px] text-zinc-500">{dim.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* The 4 Honest Questions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-3">
              <div>
                <strong className="text-xs font-mono uppercase text-emerald-400 block mb-1">
                  1. Why this project?
                </strong>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  {rec?.why_this_project}
                </p>
              </div>
              <div className="pt-2 border-t border-zinc-800/80">
                <strong className="text-xs font-mono uppercase text-emerald-400 block mb-1">
                  2. Why this issue?
                </strong>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  {rec?.why_this_issue}
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-3">
              <div>
                <strong className="text-xs font-mono uppercase text-cyan-400 block mb-1">
                  3. Why is it suitable for me?
                </strong>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  {rec?.why_suitable_for_me}
                </p>
              </div>
              <div className="pt-2 border-t border-zinc-800/80">
                <strong className="text-xs font-mono uppercase text-amber-400 block mb-1">
                  4. What should I verify first?
                </strong>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  {rec?.what_to_verify_first}
                </p>
              </div>
            </div>
          </div>

          {/* Grounded Candidate Files */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode2 className="h-4 w-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-zinc-200">
                  Evidence-Grounded Candidate Files ({inv.candidate_files.length})
                </h3>
              </div>
              <span className="text-[10px] font-mono text-zinc-500">
                SHA: {inv.commit_sha?.slice(0, 8)}
              </span>
            </div>

            <div className="space-y-2.5">
              {inv.candidate_files.map((cf: any, idx: number) => (
                <div
                  key={idx}
                  className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 font-mono text-xs">
                      <strong className="text-zinc-200">{cf.path}</strong>
                      <span className="text-zinc-500">(L{cf.start_line}-L{cf.end_line})</span>
                      <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] text-zinc-400">
                        {cf.match_type}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        cf.status === "VERIFIED" ? "bg-emerald-500/10 text-emerald-400" : "bg-cyan-500/10 text-cyan-400"
                      }`}>
                        {cf.status}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-400">{cf.reason}</p>
                  </div>
                  <span className="text-xs font-mono text-zinc-500 shrink-0">
                    Symbol: {cf.symbol}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Likely Execution Path */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-3">
            <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <Network className="h-4 w-4 text-cyan-400" />
              Traceable Execution Flow
            </h3>
            <div className="space-y-2 bg-zinc-950 p-4 rounded-lg border border-zinc-800 font-mono text-xs text-zinc-300">
              {inv.likely_execution_path.map((step: string, idx: number) => (
                <div key={idx} className="flex items-start gap-2">
                  <span className="text-emerald-400">→</span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Reality Checker Truth Matrix */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Verified Known Facts */}
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold font-mono text-emerald-400 uppercase">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>VERIFIED: Known Facts</span>
              </div>
              <ul className="space-y-1 text-xs text-zinc-300">
                {inv.known_facts.map((f: any, idx: number) => (
                  <li key={idx} className="flex items-start gap-1">
                    <span className="text-emerald-400">•</span> {f.claim}
                  </li>
                ))}
              </ul>
            </div>

            {/* Inferred Hypotheses */}
            <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-4 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold font-mono text-cyan-400 uppercase">
                <Sparkles className="h-3.5 w-3.5" />
                <span>INFERRED: Hypotheses</span>
              </div>
              <ul className="space-y-1 text-xs text-zinc-300">
                {inv.inferred_hypotheses.map((h: any, idx: number) => (
                  <li key={idx} className="flex items-start gap-1">
                    <span className="text-cyan-400">•</span> {h.claim}
                  </li>
                ))}
              </ul>
            </div>

            {/* Explicit Unknowns */}
            <div className="rounded-xl border border-purple-500/30 bg-purple-500/5 p-4 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold font-mono text-purple-400 uppercase">
                <HelpCircle className="h-3.5 w-3.5" />
                <span>UNKNOWN: Explicit Gaps</span>
              </div>
              <ul className="space-y-1 text-xs text-zinc-300">
                {inv.explicit_unknowns.map((u: any, idx: number) => (
                  <li key={idx} className="flex items-start gap-1">
                    <span className="text-purple-400">•</span> {u.claim}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Bottom Next Step Callout */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <strong className="text-xs font-semibold text-zinc-200 block">
                Next Recommended Step
              </strong>
              <p className="text-xs text-zinc-400 mt-0.5">
                {inv.minimal_next_step}
              </p>
            </div>
            <button
              onClick={() => setActiveTab("triage")}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition-colors cursor-pointer shrink-0"
            >
              Start Contributor Triage
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: CONTRIBUTOR TRIAGE & HYPOTHESES */}
      {/* ========================================================================= */}
      {activeTab === "triage" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-2">
            <h3 className="text-sm font-semibold text-zinc-200">
              Guided Triage Before Code Generation
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Maintainers value contributors who independently understand and reproduce issues before proposing code. Fill out your investigation notes, test your hypotheses, and make a conscious decision to proceed, clarify, or skip.
            </p>
          </div>

          {/* Triage Steps Form */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4 text-xs">
            {/* Step 1: Restatement */}
            <div className="space-y-1">
              <label className="font-semibold text-zinc-300 block">
                1. Restate the problem in your own words:
              </label>
              <textarea
                rows={2}
                value={triage.user_summary}
                onChange={(e) => setTriage({ ...triage, user_summary: e.target.value })}
                placeholder="What exactly fails and under what specific conditions?..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Step 2: Expected vs Actual */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="font-semibold text-zinc-300 block">
                  2a. Expected Behavior:
                </label>
                <input
                  type="text"
                  value={triage.expected_behavior}
                  onChange={(e) => setTriage({ ...triage, expected_behavior: e.target.value })}
                  placeholder="e.g. Return sensible default or log warning"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="space-y-1">
                <label className="font-semibold text-zinc-300 block">
                  2b. Actual Observed Behavior:
                </label>
                <input
                  type="text"
                  value={triage.actual_behavior}
                  onChange={(e) => setTriage({ ...triage, actual_behavior: e.target.value })}
                  placeholder="e.g. Unhandled KeyError crashing the process"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            {/* Step 3 & 4: Suspected Path & Reproduction */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="font-semibold text-zinc-300 block">
                  3. Suspected Code Path & Functions:
                </label>
                <input
                  type="text"
                  value={triage.suspected_code_path}
                  onChange={(e) => setTriage({ ...triage, suspected_code_path: e.target.value })}
                  placeholder="e.g. src/config.py lines 42-60 in Config.get"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
              <div className="space-y-1">
                <label className="font-semibold text-zinc-300 block">
                  4. Minimal Reproduction or Test Notes:
                </label>
                <input
                  type="text"
                  value={triage.reproduction_notes}
                  onChange={(e) => setTriage({ ...triage, reproduction_notes: e.target.value })}
                  placeholder="e.g. Run pytest tests/test_config.py::test_missing_key"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => handleSaveTriage()}
                disabled={savingTriage}
                className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold transition-colors cursor-pointer"
              >
                {savingTriage ? "Saving..." : "Save Triage Notes"}
              </button>
            </div>
          </div>

          {/* Step 5: Hypothesis Log */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-zinc-200">
                  5. Contributor Hypothesis Log
                </h4>
                <p className="text-xs text-zinc-400">
                  Record hypotheses, test them against the code, and confirm before changing source lines.
                </p>
              </div>
            </div>

            {/* Existing Hypotheses List */}
            <div className="space-y-3">
              {hypotheses.map((h) => (
                <div
                  key={h.id}
                  className="rounded-lg border border-zinc-800 bg-zinc-950 p-4 space-y-2 text-xs"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <strong className="text-zinc-200 font-medium">{h.hypothesis}</strong>
                      {h.supporting_evidence?.length > 0 && (
                        <div className="text-[11px] text-emerald-400 font-mono mt-1">
                          Evidence: {h.supporting_evidence.join(", ")}
                        </div>
                      )}
                    </div>

                    {/* Status Pill / Switcher */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      {(["untested", "confirmed", "rejected", "inconclusive"] as const).map((st) => (
                        <button
                          key={st}
                          onClick={() => handleUpdateHypoStatus(h.id, st)}
                          className={`px-2 py-0.5 rounded text-[10px] font-mono capitalize transition-colors cursor-pointer ${
                            h.status === st
                              ? st === "confirmed" ? "bg-emerald-500 text-zinc-950 font-bold"
                              : st === "rejected" ? "bg-red-500 text-zinc-950 font-bold"
                              : "bg-cyan-500 text-zinc-950 font-bold"
                              : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
                          }`}
                        >
                          {st}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Add Hypothesis Form */}
            <form onSubmit={handleAddHypothesis} className="bg-zinc-950 p-3.5 rounded-lg border border-zinc-800 space-y-2.5 text-xs">
              <span className="font-semibold text-zinc-300 block">Add New Hypothesis:</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Hypothesis (e.g. KeyError occurs because .get() lacks default)..."
                  value={newHypothesis}
                  onChange={(e) => setNewHypothesis(e.target.value)}
                  className="bg-zinc-900 border border-zinc-800 rounded p-2 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                />
                <input
                  type="text"
                  placeholder="Supporting evidence (e.g. line 45 config.py)..."
                  value={newEvidence}
                  onChange={(e) => setNewEvidence(e.target.value)}
                  className="bg-zinc-900 border border-zinc-800 rounded p-2 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 font-mono text-[11px]"
                />
              </div>
              <button
                type="submit"
                disabled={addingHypo || !newHypothesis.trim()}
                className="px-3 py-1.5 rounded bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" />
                Add Hypothesis to Log
              </button>
            </form>
          </div>

          {/* Step 6: Contributor Decision Gate */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 space-y-4">
            <h4 className="text-sm font-bold text-zinc-100">
              6. Contributor Decision Gate
            </h4>
            <p className="text-xs text-zinc-400">
              Based on your triage and evidence, what is the most responsible next action?
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={handleProceedToPlan}
                disabled={planning}
                className="p-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 text-left transition-all cursor-pointer group"
              >
                <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs mb-1">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Proceed to Fix</span>
                </div>
                <p className="text-[11px] text-zinc-400 group-hover:text-zinc-300">
                  Hypothesis is confirmed and reproducible. Generate an evidence-grounded implementation plan.
                </p>
              </button>

              <button
                onClick={() => setActiveTab("drafts")}
                className="p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/20 text-left transition-all cursor-pointer group"
              >
                <div className="flex items-center gap-2 text-amber-400 font-bold text-xs mb-1">
                  <HelpCircle className="h-4 w-4" />
                  <span>Ask Maintainer First</span>
                </div>
                <p className="text-[11px] text-zinc-400 group-hover:text-zinc-300">
                  Requirements or preferences are ambiguous. Use the generated communication draft to inquire politely.
                </p>
              </button>

              <button
                onClick={() => {
                  handleSaveTriage("abandon_unsuitable");
                  alert("Issue marked as abandoned. You have responsibly avoided wasted effort!");
                }}
                className="p-4 rounded-xl border border-zinc-800 bg-zinc-950 hover:bg-zinc-900 text-left transition-all cursor-pointer group"
              >
                <div className="flex items-center gap-2 text-zinc-400 font-bold text-xs mb-1">
                  <XCircle className="h-4 w-4" />
                  <span>Skip / Choose Another</span>
                </div>
                <p className="text-[11px] text-zinc-500 group-hover:text-zinc-400">
                  Scope is too broad or issue is not suitable. Return to explorer to pick a better fit.
                </p>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: MAINTAINER COMMUNICATION DRAFTS */}
      {/* ========================================================================= */}
      {activeTab === "drafts" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-2">
            <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-purple-400" />
              Maintainer-Ready Communication Templates
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Open-source maintainers receive hundreds of notifications daily. These drafts follow open-source etiquette—concise, respectful, and focused on verifiable facts.
            </p>
            <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800 text-[11px] text-zinc-400 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
              <span><strong>Safety Guarantee:</strong> FirstPatch AI never automatically posts to GitHub. You review, customize, and submit comments yourself.</span>
            </div>
          </div>

          <div className="space-y-4">
            {drafts.map((d: any) => {
              const isCopied = copiedDraft === d.draft_type;
              return (
                <div
                  key={d.draft_type}
                  className="rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden"
                >
                  <div className="px-4 py-3 bg-zinc-950 border-b border-zinc-800 flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold text-zinc-200">{d.label}</h4>
                      <span className="text-[10px] font-mono text-zinc-500">Subject: {d.subject}</span>
                    </div>
                    <button
                      onClick={() => handleCopyDraft(d.draft_type, d.body)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-mono transition-colors cursor-pointer"
                    >
                      {isCopied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                      {isCopied ? "Copied to Clipboard!" : "Copy Draft"}
                    </button>
                  </div>
                  <div className="p-4 font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed bg-zinc-950/70">
                    {d.body}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
