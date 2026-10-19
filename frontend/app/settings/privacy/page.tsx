"use client";

import { useState } from "react";
import { resetDatabase } from "@/lib/api";
import {
  ShieldCheck,
  Lock,
  EyeOff,
  Server,
  Terminal,
  AlertTriangle,
  Trash2,
  Check,
} from "lucide-react";

export default function PrivacySettingsPage() {
  const [resetting, setResetting] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);

  const handleResetDb = async () => {
    if (!confirm("Are you sure you want to reset the local database? All indexed snapshots and triage notes will be cleared.")) {
      return;
    }
    setResetting(true);
    try {
      await resetDatabase();
      setResetSuccess(true);
      setTimeout(() => setResetSuccess(false), 3000);
    } catch (e: any) {
      alert("Failed to reset database: " + e.message);
    } finally {
      setResetting(false);
    }
  };

  const privacyBoundaries = [
    {
      title: "SSRF Protection & Strict Domain Allowlist",
      desc: "All outbound HTTP requests are restricted to GitHub API and raw content domains (api.github.com, raw.githubusercontent.com). Local and internal network IPs are permanently rejected.",
      icon: Server,
    },
    {
      title: "Zero Code Execution During Ingestion",
      desc: "Repositories are analyzed statically via Abstract Syntax Tree (AST) parsing. No untrusted setup scripts, builds, or dependencies are ever executed during indexing.",
      icon: EyeOff,
    },
    {
      title: "Automatic Secret & High-Entropy Token Redaction",
      desc: "High-entropy strings, API tokens (ghp_, sk-, Bearer), passwords, and private SSH keys are scrubbed before any prompt, log, or database persistence.",
      icon: Lock,
    },
    {
      title: "Isolated Subprocess Sandbox",
      desc: "Automated verification test suites run in restricted subprocesses with strict execution timeouts (15 seconds) and memory caps.",
      icon: Terminal,
    },
    {
      title: "Local-First Architecture",
      desc: "All repository metadata, AST chunks, and hypothesis logs are stored locally in an embedded SQLite database on your machine.",
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Header */}
      <div className="border-b border-gray-200/80 pb-6">
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-600 shadow-sm">
            <ShieldCheck className="w-4 h-4" />
          </span>
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Privacy &amp; Security Boundaries</h1>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          FirstPatch AI operates under strict local-first, zero-leak sandboxing principles.
        </p>
      </div>

      {/* Boundaries Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {privacyBoundaries.map((b) => {
          const Icon = b.icon;
          return (
            <div key={b.title} className="card p-6 space-y-2">
              <div className="flex items-center gap-2 text-emerald-700">
                <Icon className="w-4 h-4" />
                <h3 className="text-sm font-bold text-gray-900">{b.title}</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">{b.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Local Storage & Database Management */}
      <div className="card p-6 sm:p-8 space-y-4 border-rose-100">
        <div className="flex items-center gap-2 text-rose-600">
          <Trash2 className="w-4 h-4" />
          <h3 className="text-sm font-bold text-gray-900">Reset Local Database</h3>
        </div>
        <p className="text-xs text-gray-500 leading-relaxed max-w-2xl">
          Clears all indexed repositories, AST chunks, triage records, and contribution workspaces from your local SQLite database.
        </p>
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleResetDb}
            disabled={resetting}
            className="btn bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs py-2 px-4 rounded-xl font-bold"
          >
            {resetting ? "Resetting…" : "Reset Database"}
          </button>
          {resetSuccess && (
            <span className="text-xs text-emerald-600 font-bold flex items-center gap-1 animate-in">
              <Check className="w-4 h-4" /> Database reset successfully!
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
