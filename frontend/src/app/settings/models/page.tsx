"use client";

import { useEffect, useState } from "react";
import { fetchModelStatus, testModelInference, updateActiveModel } from "@/lib/api";
import { Cpu, CheckCircle2, AlertCircle, RefreshCw, Terminal, Sparkles } from "lucide-react";

export default function ModelSettingsPage() {
  const [status, setStatus] = useState<any>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = () => {
    fetchModelStatus().then((res) => {
      if (res) {
        setStatus(res);
        setSelectedModel(res.active_model || "");
      }
    });
  };

  const handleTestInference = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const data = await testModelInference();
      setTestResult(data.test_output);
    } catch (e: any) {
      setTestResult(`Failed to connect to backend: ${e.message}`);
    } finally {
      setTesting(false);
    }
  };

  const handleUpdateModel = async () => {
    try {
      await updateActiveModel(selectedModel);
      loadStatus();
      alert("Active model updated successfully.");
    } catch (e: any) {
      alert("Failed to update model: " + e.message);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-medium mb-1.5">
          <Cpu className="h-3 w-3" />
          <span>Local Model Manager</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold text-zinc-100">Local AI & Ollama Configuration</h1>
        <p className="text-xs text-zinc-400 mt-0.5">
          FirstPatch AI runs reasoning and mentoring entirely on your machine using Ollama.
        </p>
      </div>

      {/* Ollama Status Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${status?.online ? "bg-emerald-500" : "bg-amber-500"}`} />
            <span className="text-sm font-semibold text-zinc-200">
              Ollama Service Status: {status?.online ? "Connected" : "Offline"}
            </span>
          </div>
          <button
            onClick={loadStatus}
            className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 cursor-pointer"
          >
            <RefreshCw className="h-3 w-3" /> Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs text-zinc-400">
          <div>Endpoint: <strong className="font-mono text-zinc-200">{status?.endpoint || "http://127.0.0.1:11434"}</strong></div>
          <div>Active Model: <strong className="font-mono text-emerald-400">{status?.active_model || "None"}</strong></div>
          <div>Embeddings Model: <strong className="font-mono text-zinc-200">{status?.embed_model || "nomic-embed-text"}</strong></div>
          <div>Installed Models: <strong className="text-zinc-200">{status?.installed_models?.length || 0}</strong></div>
        </div>

        {/* Switch Active Model */}
        {status?.installed_models?.length > 0 && (
          <div className="pt-3 border-t border-zinc-800/80 flex items-center gap-3">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 rounded-lg p-2 flex-1 focus:outline-none focus:border-emerald-500"
            >
              {status.installed_models.map((m: string) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <button
              onClick={handleUpdateModel}
              className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs cursor-pointer transition-colors"
            >
              Set as Active Model
            </button>
          </div>
        )}
      </div>

      {/* Test Inference Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-zinc-200">Verify Local Model Inference</h3>
        <p className="text-xs text-zinc-400">
          Sends a small test prompt to verify that your active model responds correctly and adheres to low temperature constraints.
        </p>

        <button
          onClick={handleTestInference}
          disabled={testing || !status?.online}
          className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          {testing ? (
            <>
              <span className="h-3 w-3 border-2 border-zinc-200 border-t-transparent rounded-full animate-spin"></span>
              Inferring...
            </>
          ) : (
            <>
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              Run Health-Check Inference
            </>
          )}
        </button>

        {testResult && (
          <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-300 font-mono">
            {testResult}
          </div>
        )}
      </div>

      {/* Recommended Models Instructions */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/20 p-5 space-y-3">
        <h3 className="text-xs font-bold font-mono uppercase text-zinc-400">How to Pull Additional Models</h3>
        <p className="text-xs text-zinc-500">
          Run these commands in your macOS terminal to download supported open-weight models:
        </p>
        <div className="space-y-1.5 font-mono text-xs text-emerald-400 bg-zinc-950 p-3 rounded-lg border border-zinc-800">
          <div>ollama pull gemma2:2b       # Lightweight general mentor (~1.6 GB)</div>
          <div>ollama pull qwen2.5-coder:3b  # Fast code reasoning model (~1.9 GB)</div>
          <div>ollama pull nomic-embed-text  # Lightweight vector embeddings (~274 MB)</div>
        </div>
      </div>
    </div>
  );
}
