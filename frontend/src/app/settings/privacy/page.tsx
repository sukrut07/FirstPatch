"use client";

import { useEffect, useState } from "react";
import { resetDatabase } from "@/lib/api";
import { ShieldCheck, Database, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function PrivacySettingsPage() {
  const [resetting, setResetting] = useState(false);
  const [resetDone, setResetDone] = useState(false);

  const handleReset = async () => {
    if (!confirm("Are you sure you want to clear all locally indexed repositories and contribution workspaces?")) {
      return;
    }
    setResetting(true);
    try {
      await resetDatabase();
      setResetDone(true);
      setTimeout(() => setResetDone(false), 4000);
    } catch (e: any) {
      alert("Reset failed: " + e.message);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-medium mb-1.5">
          <ShieldCheck className="h-3 w-3" />
          <span>Local-First Transparency</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold text-zinc-100">Privacy & Data Governance</h1>
        <p className="text-xs text-zinc-400 mt-0.5">
          FirstPatch AI operates locally on your machine with strict source code isolation.
        </p>
      </div>

      {/* Network Transparency Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-zinc-200">Network Disclosure</h3>
        <p className="text-xs text-zinc-400 leading-relaxed">
          While FirstPatch AI runs reasoning and mentoring models locally without sending prompt tokens to proprietary cloud APIs, the application makes outbound network requests for specific public resources:
        </p>
        <ul className="text-xs text-zinc-300 space-y-2 list-disc list-inside">
          <li><strong>GitHub REST API:</strong> Used exclusively to retrieve public repository metadata, file manifests, and open issues.</li>
          <li><strong>Raw GitHub Content:</strong> Downloads bounded source files for AST parsing and SQLite FTS5 lexical indexing.</li>
          <li><strong>Local Ollama Loopback:</strong> Communicates exclusively over `http://127.0.0.1:11434` without internet transmission.</li>
        </ul>
      </div>

      {/* Local Storage Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-zinc-200">Local SQLite Storage</h3>
        </div>
        <p className="text-xs text-zinc-400 leading-relaxed">
          All repository snapshots, AST symbols, code chunks, evidence ledgers, and Flight Recorder journeys are stored in a local SQLite database (`firstpatch.db`) in WAL mode.
        </p>
      </div>

      {/* Reset Database Card */}
      <div className="rounded-xl border border-red-500/30 bg-red-950/10 p-5 space-y-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-400" />
          <h3 className="text-sm font-semibold text-red-300">Reset Local Application Database</h3>
        </div>
        <p className="text-xs text-zinc-400 leading-relaxed">
          Clears all indexed repository snapshots, cached issues, conversation logs, and Flight Recorder workspaces from your local machine.
        </p>

        <button
          onClick={handleReset}
          disabled={resetting}
          className="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-400 text-zinc-950 font-semibold text-xs cursor-pointer transition-colors disabled:opacity-50"
        >
          {resetting ? "Resetting..." : "Clear Local Database"}
        </button>

        {resetDone && (
          <p className="text-xs text-emerald-400 flex items-center gap-1 font-mono">
            <CheckCircle2 className="h-3.5 w-3.5" /> All local records cleared successfully.
          </p>
        )}
      </div>
    </div>
  );
}
