"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchHealth, fetchModelStatus, listRepositories } from "@/lib/api";
import {
  Settings,
  Cpu,
  ShieldCheck,
  Server,
  ArrowRight,
  RefreshCw,
} from "lucide-react";

export default function SettingsHubPage() {
  const [health, setHealth] = useState<any>(null);
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [reposCount, setReposCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSettingsData();
  }, []);

  const loadSettingsData = async () => {
    setLoading(true);
    try {
      const [h, m, r] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchModelStatus().catch(() => null),
        listRepositories().catch(() => []),
      ]);
      setHealth(h);
      setModelStatus(m);
      setReposCount(Array.isArray(r) ? r.length : 0);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-200/80 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-xl bg-purple-50 border border-purple-200/80 flex items-center justify-center text-purple-600 shadow-sm">
              <Settings className="w-4 h-4" />
            </span>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">System Settings</h1>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Manage your AI runtime models, privacy boundaries, and local SQLite data store.
          </p>
        </div>

        <button
          onClick={loadSettingsData}
          className="btn-secondary text-xs py-2 px-3.5 rounded-xl shadow-sm inline-flex items-center gap-1.5 self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Status
        </button>
      </div>

      {/* Primary Configuration Bento */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: AI Model Configuration */}
        <Link
          href="/settings/models"
          className="card-hover p-6 sm:p-7 flex flex-col justify-between group"
        >
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-2xl bg-purple-50 border border-purple-100 flex items-center justify-center text-brand-600 shadow-sm">
                <Cpu className="w-5 h-5" />
              </div>
              <span className={`badge ${modelStatus?.online ? "badge-success" : "badge-muted"} text-[10px]`}>
                {modelStatus?.online ? "Ollama Active" : "Grounded Fallback"}
              </span>
            </div>

            <h3 className="text-lg font-bold text-gray-900 group-hover:text-brand-700 transition-colors">
              AI Models &amp; Inference
            </h3>
            <p className="text-xs text-gray-500 leading-relaxed mt-2">
              Configure local Ollama (gemma4:e2b), Google AI Studio Gemma 4 cloud keys, or DigitalOcean Gradient™ worker endpoints.
            </p>

            <div className="mt-4 pt-4 border-t border-gray-100 space-y-1.5 text-[11px] font-mono text-gray-600">
              <div className="flex justify-between">
                <span>Active Model:</span>
                <span className="font-bold text-brand-700">{modelStatus?.active_model || health?.ai_provider || "Grounded AST"}</span>
              </div>
              <div className="flex justify-between">
                <span>Inference Mode:</span>
                <span>{modelStatus?.online ? "Private Local GPU" : "Deterministic Rule Engine"}</span>
              </div>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-between text-xs font-bold text-brand-600 group-hover:text-brand-800">
            <span>Configure AI Models</span>
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>

        {/* Card 2: Privacy & Security Boundaries */}
        <Link
          href="/settings/privacy"
          className="card-hover p-6 sm:p-7 flex flex-col justify-between group"
        >
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shadow-sm">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <span className="badge-success text-[10px]">
                100% Zero-Leak
              </span>
            </div>

            <h3 className="text-lg font-bold text-gray-900 group-hover:text-brand-700 transition-colors">
              Privacy &amp; Security Boundaries
            </h3>
            <p className="text-xs text-gray-500 leading-relaxed mt-2">
              Review SSRF network allowlists, AST static parsing constraints, secret token scrubbing, and reset your local SQLite database.
            </p>

            <div className="mt-4 pt-4 border-t border-gray-100 space-y-1.5 text-[11px] font-mono text-gray-600">
              <div className="flex justify-between">
                <span>Code Execution:</span>
                <span className="text-emerald-700 font-bold">Static AST Only</span>
              </div>
              <div className="flex justify-between">
                <span>Secret Redaction:</span>
                <span className="text-emerald-700 font-bold">Active (ghp_, sk-)</span>
              </div>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-between text-xs font-bold text-brand-600 group-hover:text-brand-800">
            <span>Manage Security &amp; Data</span>
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>
      </div>

      {/* System Diagnostics Bento */}
      <div className="card p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between border-b border-gray-100 pb-4">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-brand-600" />
            <h3 className="text-sm font-bold text-gray-900">Backend Diagnostics &amp; Local Storage</h3>
          </div>
          <span className={`badge ${health?.status === "ok" ? "badge-success" : "badge-warning"} text-[10px]`}>
            {health?.status === "ok" ? "Backend Connected" : "Connecting..."}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-2xl bg-surface-50 border border-gray-100">
            <p className="text-gray-400 font-bold uppercase text-[10px]">Application Version</p>
            <p className="font-mono font-bold text-gray-900 mt-1">{health?.version || "v0.1.0"}</p>
            <p className="text-[11px] text-gray-500 mt-0.5">Environment: {health?.environment || "development"}</p>
          </div>

          <div className="p-4 rounded-2xl bg-surface-50 border border-gray-100">
            <p className="text-gray-400 font-bold uppercase text-[10px]">Indexed Codebases</p>
            <p className="font-mono font-bold text-brand-700 mt-1">{reposCount} Repositories</p>
            <p className="text-[11px] text-gray-500 mt-0.5">Stored in local SQLite database</p>
          </div>

          <div className="p-4 rounded-2xl bg-surface-50 border border-gray-100">
            <p className="text-gray-400 font-bold uppercase text-[10px]">GitHub Authentication</p>
            <p className="font-mono font-bold text-gray-900 mt-1">
              {health?.github_authenticated ? "Authenticated Token" : "Public Rate-Limited"}
            </p>
            <p className="text-[11px] text-gray-500 mt-0.5">Rate limit reset: Standard API window</p>
          </div>
        </div>
      </div>
    </div>
  );
}
