"use client";

import { useEffect, useState } from "react";
import { fetchModelStatus, testModelInference, testCloudApiKey, updateActiveModel } from "@/lib/api";
import {
  Cpu,
  CheckCircle2,
  AlertCircle,
  Key,
  Sparkles,
  RefreshCw,
  ShieldCheck,
  Zap,
  Save,
  Check,
} from "lucide-react";

export default function ModelsSettingsPage() {
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [testingInference, setTestingInference] = useState(false);
  const [inferenceResult, setInferenceResult] = useState<any>(null);

  // Cloud API Key State
  const [apiKey, setApiKey] = useState("");
  const [selectedProvider, setSelectedProvider] = useState("google_ai_studio");
  const [selectedModel, setSelectedModel] = useState("gemma-4-31b-it");
  const [testingKey, setTestingKey] = useState(false);
  const [keyResult, setKeyResult] = useState<any>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    loadStatus();
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("firstpatch_api_key") || localStorage.getItem("firstpatch_gemma_api_key") || "";
      if (saved) setApiKey(saved);
      const prov = localStorage.getItem("firstpatch_provider") || "google_ai_studio";
      setSelectedProvider(prov);
    }
  }, []);

  const loadStatus = () => {
    setLoading(true);
    fetchModelStatus()
      .then((res) => { if (res) setModelStatus(res); })
      .finally(() => setLoading(false));
  };

  const handleTestInference = async () => {
    setTestingInference(true);
    setInferenceResult(null);
    try {
      const res = await testModelInference();
      setInferenceResult(res);
    } catch (err: any) {
      setInferenceResult({ status: "error", detail: err.message || "Inference check failed." });
    } finally {
      setTestingInference(false);
    }
  };

  const handleSaveAndTestKey = async () => {
    if (!apiKey.trim()) {
      localStorage.removeItem("firstpatch_api_key");
      localStorage.removeItem("firstpatch_gemma_api_key");
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2000);
      return;
    }

    setTestingKey(true);
    setKeyResult(null);
    try {
      const res = await testCloudApiKey(apiKey.trim(), selectedProvider, selectedModel);
      setKeyResult({ status: "success", detail: "API Key verified successfully!" });
      if (typeof window !== "undefined") {
        localStorage.setItem("firstpatch_api_key", apiKey.trim());
        localStorage.setItem("firstpatch_gemma_api_key", apiKey.trim());
        localStorage.setItem("firstpatch_provider", selectedProvider);
      }
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err: any) {
      setKeyResult({ status: "error", detail: err.message || "Failed to verify API Key." });
    } finally {
      setTestingKey(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-200/80 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-xl bg-purple-50 border border-purple-200/80 flex items-center justify-center text-purple-600 shadow-sm">
              <Cpu className="w-4 h-4" />
            </span>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">AI Model Configuration</h1>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Configure local Ollama, Google AI Studio Gemma 4, or DigitalOcean Gradient™ worker execution.
          </p>
        </div>

        <button
          onClick={loadStatus}
          className="btn-secondary text-xs py-2 px-3.5 rounded-xl shadow-sm inline-flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Status
        </button>
      </div>

      {/* Model Providers Status Bento */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        {/* Local Ollama Card */}
        <div className="card p-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="section-label text-brand-700">Local Ollama</span>
            <span className={`badge ${modelStatus?.online ? "badge-success" : "badge-muted"} text-[10px]`}>
              {modelStatus?.online ? "ONLINE" : "OFFLINE"}
            </span>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed">
            Local zero-leak inference running on localhost:11434 with gemma4:e2b or llama3.
          </p>
          <div className="text-[11px] font-mono text-gray-500">
            Model: {modelStatus?.active_model || "Not Connected"}
          </div>
        </div>

        {/* Cloud LLM / Gemma 4 Card */}
        <div className="card p-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="section-label text-purple-700">Cloud Gemma 4</span>
            <span className="badge-brand text-[10px]">CONFIGURABLE</span>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed">
            High-throughput architecture analysis via Google AI Studio or DigitalOcean Gradient™.
          </p>
          <div className="text-[11px] font-mono text-gray-500">
            Key: {apiKey ? "••••••••" + apiKey.slice(-4) : "Not Configured"}
          </div>
        </div>

        {/* Deterministic AST Fallback */}
        <div className="card p-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="section-label text-emerald-700">AST Fallback</span>
            <span className="badge-success text-[10px]">ALWAYS READY</span>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed">
            100% deterministic Python AST parsing and regex heuristics that never fail or leak data.
          </p>
          <div className="text-[11px] font-mono text-emerald-700 font-bold">
            Guaranteed Offline Operation
          </div>
        </div>
      </div>

      {/* Cloud Key Configuration Bento */}
      <div className="card p-6 sm:p-8 space-y-6">
        <div>
          <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <Key className="w-4 h-4 text-brand-600" />
            Cloud AI Key (Optional)
          </h2>
          <p className="text-xs text-gray-500 mt-1">
            Store your Google AI Studio or DigitalOcean key strictly in your local browser storage. It is never logged or exposed.
          </p>
        </div>

        <div className="space-y-4 max-w-xl">
          <div>
            <label className="section-label text-gray-700 block mb-1">Provider</label>
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className="input text-xs py-2"
            >
              <option value="google_ai_studio">Google AI Studio (Gemini / Gemma 4 API)</option>
              <option value="do_gradient">DigitalOcean Gradient™ Agentic Worker</option>
            </select>
          </div>

          <div>
            <label className="section-label text-gray-700 block mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="AIzaSy... or secret key"
              className="input text-xs font-mono py-2.5"
            />
          </div>

          <div>
            <label className="section-label text-gray-700 block mb-1">Model Name</label>
            <input
              type="text"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="input text-xs font-mono py-2"
            />
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSaveAndTestKey}
              disabled={testingKey}
              className="btn-primary text-xs py-2.5 px-5 rounded-2xl shadow-md inline-flex items-center gap-1.5"
            >
              {testingKey ? "Verifying…" : "Save & Verify API Key"}
            </button>
            {savedSuccess && (
              <span className="text-xs text-emerald-600 font-bold flex items-center gap-1 animate-in">
                <Check className="w-4 h-4" /> Saved!
              </span>
            )}
          </div>

          {keyResult && (
            <div
              className={`p-3 rounded-xl text-xs font-semibold ${
                keyResult.status === "success"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "bg-rose-50 text-rose-800 border border-rose-200"
              }`}
            >
              {keyResult.detail}
            </div>
          )}
        </div>
      </div>

      {/* Model Health Check & Diagnostics */}
      <div className="card p-6 space-y-4">
        <div>
          <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <Zap className="w-4 h-4 text-purple-600" />
            Live Model Inference Diagnostics
          </h2>
          <p className="text-xs text-gray-500 mt-1">
            Test round-trip inference latency and health against active model providers.
          </p>
        </div>

        <button
          onClick={handleTestInference}
          disabled={testingInference}
          className="btn-secondary text-xs py-2 px-4 rounded-xl font-bold"
        >
          {testingInference ? "Running Health Check…" : "Run Inference Health Check"}
        </button>

        {inferenceResult && (
          <div className="p-4 rounded-2xl bg-surface-100 border border-gray-200 text-xs font-mono text-gray-800 animate-in">
            <pre className="whitespace-pre-wrap">{JSON.stringify(inferenceResult, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
