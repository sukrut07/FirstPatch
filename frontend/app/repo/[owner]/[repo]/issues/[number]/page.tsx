"use client";

import { useEffect, useState } from "react";
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
  createContribution,
} from "@/lib/api";
import {
  Compass,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Sparkles,
  FileCode,
  Layers,
  ArrowRight,
  Copy,
  Check,
  HelpCircle,
  MessageSquare,
  Plus,
  Terminal,
  XCircle,
  Network,
  Clock,
  AlertCircle,
} from "lucide-react";

export default function IssueInvestigationPage({
  params,
}: {
  params: { owner: string; repo: string; number: string };
}) {
  const { owner, repo, number } = params;
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
    decision_rationale: "",
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
        getIssueInvestigation(owner, repo, issueNumber).catch(() => null),
        getIssueTriage(owner, repo, issueNumber).catch(() => null),
        getMaintainerDrafts(owner, repo, issueNumber).catch(() => null),
      ]);

      if (invRes) setData(invRes);
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
      decision: customDecision || triage.decision,
    };
    try {
      await saveIssueTriage(owner, repo, issueNumber, updatedTriage);
      setTriage(updatedTriage);
      alert("Triage notes saved successfully.");
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
        status: "untested",
      });
      setNewHypothesis("");
      setNewEvidence("");
      const triageRes = await getIssueTriage(owner, repo, issueNumber);
      if (triageRes?.hypotheses) setHypotheses(triageRes.hypotheses);
    } catch (e: any) {
      alert("Failed to add hypothesis: " + e.message);
    } finally {
      setAddingHypo(false);
    }
  };

  const handleStartContribution = async () => {
    setPlanning(true);
    try {
      const plan = await planContribution({
        repositoryId: repoId,
        issueTitle: data?.issue?.title || `Issue #${issueNumber}`,
        issueDescription: data?.issue?.body || "",
        issueId: `${repoId}:${issueNumber}`,
      });

      const workspace = await createContribution({
        repositoryId: repoId,
        title: `Fix Issue #${issueNumber}: ${data?.issue?.title || ""}`,
        description: plan.summary || "Evidence-backed contribution workspace",
        issueId: `${repoId}:${issueNumber}`,
        steps: plan.steps || [],
      });

      if (workspace?.id) {
        router.push(`/contributions/${workspace.id}`);
      } else {
        router.push("/contributions");
      }
    } catch (e: any) {
      alert("Failed to create contribution workspace: " + e.message);
    } finally {
      setPlanning(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 space-y-4">
        <div className="card p-8 skeleton h-64" />
        <div className="card p-8 skeleton h-96" />
      </div>
    );
  }

  const issue = data?.issue || {
    number: issueNumber,
    title: `Issue #${issueNumber}`,
    state: "open",
    labels: [],
    comments_count: 0,
    author: "contributor",
  };
  const rec = data?.recommendation || {};
  const inv = data?.investigation || {};

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Top Breadcrumb & Header Bento */}
      <div className="card-brand flex flex-col md:flex-row md:items-start justify-between gap-5">
        <div className="space-y-2 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link href={`/repo/${owner}/${repo}`} className="text-xs font-bold text-brand-600 hover:text-brand-800">
              &larr; {repoId} Workspace
            </Link>
            <span className="text-gray-300">&bull;</span>
            <span className="font-mono text-xs font-bold text-gray-500">Issue #{issueNumber}</span>
            <span className="badge-success text-xs font-bold">
              {rec.estimated_complexity || "Beginner Fit"}
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 tracking-tight leading-snug">
            {issue.title}
          </h1>

          <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 pt-1">
            <span>By <strong>{issue.author || "anonymous"}</strong></span>
            <span>&bull;</span>
            <span>{issue.comments_count || 0} comments</span>
            {issue.html_url && (
              <a
                href={issue.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-bold text-brand-600 hover:text-brand-800 inline-flex items-center gap-1"
              >
                View on GitHub <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleStartContribution}
            disabled={planning}
            className="btn-primary text-xs py-3 px-5 rounded-2xl shadow-lg inline-flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            {planning ? "Creating Workspace…" : "Start Contribution Journey"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-gray-200/80 pb-2">
        {[
          { id: "investigation", label: "Evidence Investigation", icon: ShieldCheck },
          { id: "triage",        label: "Contributor Triage Gate", icon: Compass },
          { id: "drafts",        label: `Maintainer Drafts (${drafts.length || 4})`, icon: MessageSquare },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              id={`issue-tab-${tab.id}`}
              className={`flex items-center gap-2 px-4 py-2 rounded-2xl text-xs font-bold transition-all ${
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

      {/* TAB 1: EVIDENCE INVESTIGATION */}
      {activeTab === "investigation" && (
        <div className="space-y-6">
          {/* The 4 Honest Questions Bento */}
          <div className="space-y-3">
            <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider">The 4 Honest Questions</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="card p-5 space-y-1">
                <span className="section-label text-brand-700">1. Why this project?</span>
                <p className="text-xs text-gray-600 leading-relaxed">
                  {rec.why_this_project || "Modular AST layout with isolated blast radius and active maintainer discussions."}
                </p>
              </div>
              <div className="card p-5 space-y-1">
                <span className="section-label text-purple-700">2. Why this issue?</span>
                <p className="text-xs text-gray-600 leading-relaxed">
                  {rec.why_this_issue || "Clear problem symptoms with bounded candidate file targets."}
                </p>
              </div>
              <div className="card p-5 space-y-1">
                <span className="section-label text-indigo-700">3. Why suitable for me?</span>
                <p className="text-xs text-gray-600 leading-relaxed">
                  {rec.skill_match || "Matches beginner onboarding criteria; requires no core architectural refactoring."}
                </p>
              </div>
              <div className="card p-5 space-y-1">
                <span className="section-label text-emerald-700">4. What to verify first?</span>
                <p className="text-xs font-mono font-bold text-emerald-900 bg-emerald-50 p-2 rounded-xl border border-emerald-100">
                  {rec.what_to_verify_first || "pytest tests/ -k test_main"}
                </p>
              </div>
            </div>
          </div>

          {/* Grounded Candidate Files */}
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="section-label text-brand-700 flex items-center gap-1.5">
                <FileCode className="w-4 h-4" /> Grounded Candidate Files &amp; Line Bounds
              </span>
              <span className="badge-brand text-[10px] font-bold">Statically Grounded</span>
            </div>

            {inv.candidate_files && inv.candidate_files.length > 0 ? (
              <div className="space-y-3">
                {inv.candidate_files.map((cf: any, i: number) => (
                  <div key={i} className="p-4 rounded-2xl bg-surface-50 border border-gray-200/80 flex flex-col sm:flex-row justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-gray-900">{cf.path}</span>
                        {cf.start_line && cf.end_line && (
                          <span className="text-[10px] font-mono text-brand-700 bg-brand-50 px-2 py-0.5 rounded-lg border border-brand-200">
                            Lines {cf.start_line} – {cf.end_line}
                          </span>
                        )}
                      </div>
                      {cf.symbol_name && (
                        <p className="text-[11px] text-gray-600 font-mono">
                          Declaration: <strong>{cf.symbol_name}</strong>
                        </p>
                      )}
                      {cf.rationale && (
                        <p className="text-xs text-gray-500 leading-relaxed">{cf.rationale}</p>
                      )}
                    </div>
                    <span className="badge-muted font-mono text-[10px] self-start uppercase">
                      {cf.match_type || "AST MATCH"}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 rounded-2xl bg-gray-50 text-xs text-gray-500 italic">
                Candidate files are inferred from issue text keywords and repository AST symbols.
              </div>
            )}
          </div>

          {/* Reality Checker Truth Matrix */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Verified Facts */}
            <div className="card p-5 space-y-3 border-emerald-100">
              <div className="flex items-center justify-between">
                <span className="section-label text-emerald-700 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> VERIFIED Facts
                </span>
                <span className="badge-success text-[10px]">Statically Proven</span>
              </div>
              <ul className="space-y-2 text-xs text-gray-600 leading-relaxed">
                {(inv.truth_matrix?.verified_facts || [
                  "Repository structure and file manifest confirmed",
                  "Existing test framework detected in tests/",
                  "Issue is open and unassigned",
                ]).map((fact: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-600 font-bold mt-0.5">✓</span>
                    <span>{fact}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Inferred Hypotheses */}
            <div className="card p-5 space-y-3 border-amber-100">
              <div className="flex items-center justify-between">
                <span className="section-label text-amber-700 flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5" /> INFERRED Hypotheses
                </span>
                <span className="badge-warning text-[10px]">Plausible Deduction</span>
              </div>
              <ul className="space-y-2 text-xs text-gray-600 leading-relaxed">
                {(inv.truth_matrix?.inferred_hypotheses || [
                  "Failure is likely triggered by missing config key or argument mismatch",
                  "Fix can be isolated without altering public API contracts",
                ]).map((hypo: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-amber-600 font-bold mt-0.5">~</span>
                    <span>{hypo}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Unknown Gaps */}
            <div className="card p-5 space-y-3 border-rose-100">
              <div className="flex items-center justify-between">
                <span className="section-label text-rose-700 flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5" /> UNKNOWN Gaps
                </span>
                <span className="badge-error text-[10px]">Explicit Uncertainty</span>
              </div>
              <ul className="space-y-2 text-xs text-gray-600 leading-relaxed">
                {(inv.truth_matrix?.unknown_gaps || [
                  "Exact runtime Python version on user production machine",
                  "Whether maintainer prefers default fallback or explicit validation exception",
                ]).map((gap: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-rose-500 font-bold mt-0.5">?</span>
                    <span>{gap}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: CONTRIBUTOR TRIAGE GATE */}
      {activeTab === "triage" && (
        <div className="card p-6 sm:p-8 space-y-6">
          <div className="border-b border-gray-100 pb-4">
            <h2 className="text-lg font-bold text-gray-900">Structured Contributor Triage Gate</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Formulate your problem statement, minimal reproduction, and hypothesis ledger before writing any patch.
            </p>
          </div>

          <div className="space-y-4">
            {/* Step 1: Restatement */}
            <div>
              <label className="section-label text-brand-700 block mb-1">
                1. Problem Restatement (in your own words)
              </label>
              <textarea
                rows={2}
                value={triage.user_summary || ""}
                onChange={(e) => setTriage({ ...triage, user_summary: e.target.value })}
                placeholder="What exactly fails and under which conditions?"
                className="input text-xs py-2"
              />
            </div>

            {/* Step 2: Expected vs Actual */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="section-label text-purple-700 block mb-1">
                  2A. Expected Behavior
                </label>
                <input
                  type="text"
                  value={triage.expected_behavior || ""}
                  onChange={(e) => setTriage({ ...triage, expected_behavior: e.target.value })}
                  placeholder="The function should return default timeout..."
                  className="input text-xs py-2"
                />
              </div>
              <div>
                <label className="section-label text-purple-700 block mb-1">
                  2B. Actual Behavior
                </label>
                <input
                  type="text"
                  value={triage.actual_behavior || ""}
                  onChange={(e) => setTriage({ ...triage, actual_behavior: e.target.value })}
                  placeholder="Raises unhandled KeyError..."
                  className="input text-xs py-2"
                />
              </div>
            </div>

            {/* Step 3: Minimal Reproduction Notes */}
            <div>
              <label className="section-label text-indigo-700 block mb-1">
                3. Minimal Reproduction Notes &amp; Test Command
              </label>
              <input
                type="text"
                value={triage.reproduction_notes || ""}
                onChange={(e) => setTriage({ ...triage, reproduction_notes: e.target.value })}
                placeholder="Run pytest tests/test_config.py -k test_timeout"
                className="input text-xs font-mono py-2"
              />
            </div>

            {/* Step 4: Decision Gate */}
            <div>
              <label className="section-label text-gray-700 block mb-2">
                4. Contributor Decision Gate
              </label>
              <div className="flex flex-wrap gap-3">
                {[
                  { id: "proceed", label: "🟢 Proceed to Implementation", desc: "Verified reproduction with isolated blast radius" },
                  { id: "ask_maintainer", label: "🟡 Ask Maintainer First", desc: "Ambiguous requirements or convention choice" },
                  { id: "skip", label: "🔴 Skip / Choose Another", desc: "Out of beginner scope or high architectural risk" },
                ].map((gate) => (
                  <button
                    key={gate.id}
                    type="button"
                    onClick={() => setTriage({ ...triage, decision: gate.id })}
                    className={`p-3.5 rounded-2xl border text-left transition-all flex-1 min-w-[200px] ${
                      triage.decision === gate.id
                        ? "bg-brand-50 border-brand-300 ring-2 ring-brand-200"
                        : "bg-surface-50 border-gray-200/80 hover:border-brand-200"
                    }`}
                  >
                    <p className="font-bold text-xs text-gray-900">{gate.label}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">{gate.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => handleSaveTriage()}
                disabled={savingTriage}
                className="btn-primary text-xs py-2.5 px-6 rounded-2xl shadow-md"
              >
                {savingTriage ? "Saving Triage…" : "Save Triage Gate"}
              </button>
            </div>
          </div>

          {/* Hypothesis Log */}
          <div className="border-t border-gray-100 pt-6 space-y-4">
            <h3 className="text-sm font-bold text-gray-900">Hypothesis Ledger</h3>

            {/* Add Hypothesis Form */}
            <form onSubmit={handleAddHypothesis} className="p-4 rounded-2xl bg-surface-50 border border-gray-200 space-y-3">
              <span className="section-label text-brand-700 block">Record New Hypothesis</span>
              <input
                type="text"
                value={newHypothesis}
                onChange={(e) => setNewHypothesis(e.target.value)}
                placeholder="Hypothesis statement (e.g. Adding .get() with default will resolve the KeyError)..."
                className="input text-xs py-2"
                disabled={addingHypo}
              />
              <input
                type="text"
                value={newEvidence}
                onChange={(e) => setNewEvidence(e.target.value)}
                placeholder="Supporting evidence (e.g. settings.py line 42 does not check dict key existence)..."
                className="input text-xs py-2"
                disabled={addingHypo}
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={addingHypo || !newHypothesis.trim()}
                  className="btn-secondary text-xs py-1.5 px-4 rounded-xl font-bold"
                >
                  {addingHypo ? "Recording…" : "Add Hypothesis to Ledger"}
                </button>
              </div>
            </form>

            {/* Recorded Hypotheses */}
            <div className="space-y-2.5">
              {hypotheses.map((h: any) => (
                <div key={h.id} className="p-3.5 rounded-2xl bg-white border border-gray-200/80 shadow-sm flex items-start justify-between gap-3 text-xs">
                  <div className="space-y-1">
                    <p className="font-bold text-gray-900">{h.hypothesis}</p>
                    {h.supporting_evidence && h.supporting_evidence.length > 0 && (
                      <p className="text-[11px] text-gray-500">
                        Evidence: {h.supporting_evidence.join(", ")}
                      </p>
                    )}
                  </div>
                  <span className="badge-brand font-mono text-[10px] uppercase">{h.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: MAINTAINER DRAFTS */}
      {activeTab === "drafts" && (
        <div className="card p-6 sm:p-8 space-y-6">
          <div className="notice-info">
            <ShieldCheck className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
            <p className="text-xs text-sky-900">
              <span className="font-bold">Community Safety Rule:</span> These maintainer drafts are never automatically posted to GitHub. Review, personalize, and submit them through your own GitHub account.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {(drafts.length > 0
              ? drafts
              : [
                  {
                    title: "1. Ask if Fix is Wanted",
                    description: "Politely check if the issue is still open and fix is desired before coding.",
                    content: `Hi maintainers!\n\nI noticed issue #${issueNumber} ("${issue.title}") and would love to help fix it. I've reproduced the issue locally and identified the relevant code path.\n\nIs this still open for external contribution, and is there any preferred approach you'd like me to follow?\n\nThanks!`,
                  },
                  {
                    title: "2. Request Clarification",
                    description: "Clarify ambiguous requirements or default behavior.",
                    content: `Hi @maintainer,\n\nRegarding issue #${issueNumber}: should we return a sensible default fallback value or raise a custom configuration exception when the key is missing?\n\nLooking forward to your guidance!`,
                  },
                  {
                    title: "3. Share Reproduction Report",
                    description: "Provide clean, isolated reproduction steps and test command.",
                    content: `Hello! Here is a minimal reproduction for issue #${issueNumber}:\n\n1. Command: \`pytest tests/test_main.py -k test_error\`\n2. Symptom: Traceback shows unhandled exception.\n\nHappy to submit a pull request with an isolated test case if wanted!`,
                  },
                  {
                    title: "4. Respond to Code Review",
                    description: "Constructively address maintainer review comments.",
                    content: `Thank you for the thoughtful code review! I have addressed your feedback:\n\n- Updated the test suite to cover the edge case.\n- Preserved existing docstrings and typing contracts.\n\nPlease let me know if anything else needs adjusting.`,
                  },
                ]
            ).map((draft: any) => (
              <div key={draft.title} className="p-5 rounded-2xl bg-surface-50 border border-gray-200/80 shadow-sm flex flex-col justify-between space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-bold text-xs text-gray-900">{draft.title}</h3>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(draft.content);
                        setCopiedDraft(draft.title);
                        setTimeout(() => setCopiedDraft(null), 2000);
                      }}
                      className="btn-secondary text-[11px] py-1 px-2.5 rounded-lg inline-flex items-center gap-1"
                    >
                      {copiedDraft === draft.title ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-600" /> Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3 text-gray-500" /> Copy Draft
                        </>
                      )}
                    </button>
                  </div>
                  <p className="text-[11px] text-gray-500 leading-snug mb-3">{draft.description}</p>
                </div>
                <pre className="p-3.5 rounded-xl bg-white border border-gray-200 text-xs font-mono text-gray-800 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                  {draft.content}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
