"use client";

import { useEffect, useState } from "react";
import { fetchModelStatus, testModelInference, updateActiveModel, testCloudApiKey } from "@/lib/api";
import {
  Cpu,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Key,
  Eye,
  EyeOff,
  ExternalLink,
  ShieldCheck,
  Zap,
  Layers
} from "lucide-react";

export default function ModelSettingsPage() {
  const [status, setStatus] = useState<any>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [testingOllama, setTestingOllama] = useState(false);
  const [ollamaTestResult, setOllamaTestResult] = useState<string | null>(null);

  // Gemma 4 API Key state
  const [gemmaApiKey, setGemmaApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [gemmaProvider, setGemmaProvider] = useState("google_ai_studio");
  const [gemmaModel, setGemmaModel] = useState("gemma-4-31b-it");
  const [customModel, setCustomModel] = useState("");
  const [autoAnalyze, setAutoAnalyze] = useState(true);
  const [testingCloud, setTestingCloud] = useState(false);
  const [cloudTestResult, setCloudTestResult] = useState<{
    status: string;
    message: string;
    details?: any;
  } | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
    loadStoredKeys();
  }, []);

  const loadStatus = () => {
    fetchModelStatus().then((res) => {
      if (res) {
        setStatus(res);
        setSelectedModel(res.active_model || "");
      }
    });
  };

  const loadStoredKeys = () => {
    if (typeof window === "undefined") return;
    const storedGemma = localStorage.getItem("firstpatch_gemma_api_key") || localStorage.getItem("firstpatch_api_key") || "";
    const storedProvider = localStorage.getItem("firstpatch_provider") || "google_ai_studio";
    const storedModel = localStorage.getItem("firstpatch_model") || "gemma-4-31b-it";
    const storedAuto = localStorage.getItem("firstpatch_gemma_auto_analyze");

    setGemmaApiKey(storedGemma);
    setGemmaProvider(storedProvider);
    if (["gemma-4-31b-it", "gemma-4-26b", "gemma-2-9b-it", "google/gemma-4-31b-it"].includes(storedModel)) {
      setGemmaModel(storedModel);
    } else if (storedModel) {
      setGemmaModel("custom");
      setCustomModel(storedModel);
    }
    if (storedAuto !== null) {
      setAutoAnalyze(storedAuto === "true");
    }
  };

  const handleSaveGemmaSettings = () => {
    if (typeof window === "undefined") return;
    const trimmed = gemmaApiKey.trim();
    const effectiveModel = gemmaModel === "custom" ? customModel.trim() : gemmaModel;

    localStorage.setItem("firstpatch_gemma_api_key", trimmed);
    localStorage.setItem("firstpatch_api_key", trimmed);
    localStorage.setItem("firstpatch_provider", gemmaProvider);
    localStorage.setItem("firstpatch_model", effectiveModel || "gemma-4-31b-it");
    localStorage.setItem("firstpatch_gemma_auto_analyze", autoAnalyze ? "true" : "false");

    setSaveMessage("Gemma 4 configuration saved successfully!");
    setTimeout(() => setSaveMessage(null), 3000);
  };

  const handleClearGemmaSettings = () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem("firstpatch_gemma_api_key");
    localStorage.removeItem("firstpatch_api_key");
    setGemmaApiKey("");
    setCloudTestResult(null);
    setSaveMessage("Gemma 4 API key cleared.");
    setTimeout(() => setSaveMessage(null), 3000);
  };

  const handleTestCloudInference = async () => {
    const keyToTest = gemmaApiKey.trim();
    if (!keyToTest) {
      setCloudTestResult({
        status: "error",
        message: "Please enter a valid Gemma 4 or Google AI Studio API key first."
      });
      return;
    }

    setTestingCloud(true);
    setCloudTestResult(null);
    const effectiveModel = gemmaModel === "custom" ? customModel.trim() : gemmaModel;

    try {
      const res = await testCloudApiKey(keyToTest, gemmaProvider, effectiveModel);
      setCloudTestResult({
        status: "success",
        message: res.test_output || "Connection verified! Gemma 4 is operational.",
        details: {
          model: res.model,
          provider: res.provider
        }
      });
    } catch (e: any) {
      setCloudTestResult({
        status: "error",
        message: e.message || "Failed to connect to Gemma 4 endpoint. Check API key."
      });
    } finally {
      setTestingCloud(false);
    }
  };

  const handleTestOllamaInference = async () => {
    setTestingOllama(true);
    setOllamaTestResult(null);
    try {
      const data = await testModelInference();
      setOllamaTestResult(data.test_output);
    } catch (e: any) {
      setOllamaTestResult(`Failed to connect to Ollama: ${e.message}`);
    } finally {
      setTestingOllama(false);
    }
  };

  const handleUpdateOllamaModel = async () => {
    try {
      await updateActiveModel(selectedModel);
      loadStatus();
      alert("Active local model updated successfully.");
    } catch (e: any) {
      alert("Failed to update model: " + e.message);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-400 text-xs font-medium mb-1.5">
          <Sparkles className="h-3 w-3" />
          <span>AI Intelligence & Model Settings</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold text-zinc-100">Gemma 4 & Model Engine Settings</h1>
        <p className="text-xs text-zinc-400 mt-0.5">
          Configure Google AI Studio Gemma 4 for complete repository intelligence, or fallback to local Ollama.
        </p>
      </div>

      {/* Gemma 4 Dedicated API Key Section */}
      <div className="rounded-xl border border-indigo-500/30 bg-gradient-to-b from-indigo-950/20 via-zinc-900/40 to-zinc-950/60 p-6 space-y-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-72 h-72 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800/80 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Key className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                Gemma 4 API Key Space
                <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Deep Repo Analysis
                </span>
              </h2>
              <p className="text-xs text-zinc-400">
                Power automated architecture pattern extraction, beginner safety scoring, and deep repo understanding.
              </p>
            </div>
          </div>
          <a
            href="https://aistudio.google.com/app/apikey"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            <span>Get Google AI Key</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>

        {/* API Key Input */}
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-300 flex items-center justify-between">
              <span>Gemma 4 / Google AI Studio API Key</span>
              <span className="text-[11px] text-zinc-500">Stored locally in your browser</span>
            </label>
            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                value={gemmaApiKey}
                onChange={(e) => setGemmaApiKey(e.target.value)}
                placeholder="AIzaSy... or OpenRouter sk-or-..."
                className="w-full bg-zinc-950/80 border border-zinc-800 rounded-lg px-3.5 py-2.5 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 font-mono pr-10"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
                title={showKey ? "Hide key" : "Show key"}
              >
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <p className="text-[11px] text-zinc-500">
              Works directly with Google AI Studio keys (<code>AIza...</code>) and OpenRouter keys (<code>sk-or-...</code>).
            </p>
          </div>

          {/* Model and Provider Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Provider</label>
              <select
                value={gemmaProvider}
                onChange={(e) => setGemmaProvider(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="google_ai_studio">Google AI Studio (Recommended)</option>
                <option value="openrouter">OpenRouter (google/gemma-4-31b-it)</option>
                <option value="openai">OpenAI Compatible Endpoint</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Model</label>
              <select
                value={gemmaModel}
                onChange={(e) => setGemmaModel(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="gemma-4-31b-it">gemma-4-31b-it (Google AI Studio Gemma 4)</option>
                <option value="gemma-4-26b">gemma-4-26b</option>
                <option value="gemma-2-9b-it">gemma-2-9b-it</option>
                <option value="google/gemma-4-31b-it">google/gemma-4-31b-it (OpenRouter)</option>
                <option value="custom">Custom Model Name...</option>
              </select>
            </div>
          </div>

          {gemmaModel === "custom" && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Custom Model Identifier</label>
              <input
                type="text"
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                placeholder="e.g. gemma-4-31b-it or custom deployment"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          )}

          {/* Auto-Analyze Checkbox */}
          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="autoAnalyzeToggle"
              checked={autoAnalyze}
              onChange={(e) => setAutoAnalyze(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-700 bg-zinc-950 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
            />
            <label htmlFor="autoAnalyzeToggle" className="text-xs text-zinc-300 cursor-pointer select-none">
              Automatically run Gemma 4 Deep Architectural Analysis whenever a new repository is indexed
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={handleSaveGemmaSettings}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center gap-1.5 transition-colors cursor-pointer shadow-sm shadow-indigo-600/30"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              Save Gemma 4 Settings
            </button>

            <button
              onClick={handleTestCloudInference}
              disabled={testingCloud || !gemmaApiKey.trim()}
              className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
            >
              {testingCloud ? (
                <>
                  <span className="h-3 w-3 border-2 border-zinc-200 border-t-transparent rounded-full animate-spin" />
                  Testing Gemma 4...
                </>
              ) : (
                <>
                  <Zap className="h-3.5 w-3.5 text-amber-400" />
                  Verify & Test Gemma 4
                </>
              )}
            </button>

            {gemmaApiKey && (
              <button
                onClick={handleClearGemmaSettings}
                className="px-3 py-2 text-xs text-zinc-500 hover:text-red-400 transition-colors cursor-pointer ml-auto"
              >
                Clear Key
              </button>
            )}
          </div>

          {saveMessage && (
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{saveMessage}</span>
            </div>
          )}

          {/* Test Feedback */}
          {cloudTestResult && (
            <div
              className={`p-3.5 rounded-lg border text-xs space-y-1.5 ${
                cloudTestResult.status === "success"
                  ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-300"
                  : "bg-red-950/20 border-red-500/30 text-red-300"
              }`}
            >
              <div className="flex items-center gap-2 font-medium">
                {cloudTestResult.status === "success" ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-red-400" />
                )}
                <span>
                  {cloudTestResult.status === "success"
                    ? "Gemma 4 Verification Succeeded"
                    : "Gemma 4 Verification Failed"}
                </span>
              </div>
              <p className="font-mono text-[11px] leading-relaxed pl-6">
                {cloudTestResult.message}
              </p>
              {cloudTestResult.details && (
                <div className="pl-6 pt-1 flex items-center gap-3 text-[10px] text-zinc-400">
                  <span>Model: <strong className="text-zinc-200">{cloudTestResult.details.model}</strong></span>
                  <span>Provider: <strong className="text-zinc-200">{cloudTestResult.details.provider}</strong></span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Feature Highlights Banner */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-zinc-800/80 text-xs">
          <div className="p-2.5 rounded-lg bg-zinc-950/50 border border-zinc-800/60 space-y-1">
            <div className="font-medium text-zinc-200 flex items-center gap-1.5">
              <Layers className="h-3 w-3 text-indigo-400" />
              <span>Architecture Patterns</span>
            </div>
            <p className="text-[11px] text-zinc-400">
              Automatically discovers whether a repo uses Hexagonal, MVC, or Pipeline design.
            </p>
          </div>
          <div className="p-2.5 rounded-lg bg-zinc-950/50 border border-zinc-800/60 space-y-1">
            <div className="font-medium text-zinc-200 flex items-center gap-1.5">
              <ShieldCheck className="h-3 w-3 text-emerald-400" />
              <span>Beginner Safe Zones</span>
            </div>
            <p className="text-[11px] text-zinc-400">
              Flags low-risk modules and safe entrypoints suited for first pull requests.
            </p>
          </div>
          <div className="p-2.5 rounded-lg bg-zinc-950/50 border border-zinc-800/60 space-y-1">
            <div className="font-medium text-zinc-200 flex items-center gap-1.5">
              <Zap className="h-3 w-3 text-amber-400" />
              <span>Zero Zero-Day Leak</span>
            </div>
            <p className="text-[11px] text-zinc-400">
              Key remains on your device or in server memory; never committed or leaked.
            </p>
          </div>
        </div>
      </div>

      {/* Ollama Local Engine Status Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${status?.online ? "bg-emerald-500" : "bg-amber-500"}`} />
            <span className="text-sm font-semibold text-zinc-200">
              Local Ollama Service: {status?.online ? "Connected" : "Offline / Standby"}
            </span>
          </div>
          <button
            onClick={loadStatus}
            className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 cursor-pointer transition-colors"
          >
            <RefreshCw className="h-3 w-3" /> Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs text-zinc-400">
          <div>Endpoint: <strong className="font-mono text-zinc-200">{status?.endpoint || "http://127.0.0.1:11434"}</strong></div>
          <div>Active Local Model: <strong className="font-mono text-emerald-400">{status?.active_model || "None"}</strong></div>
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
              onClick={handleUpdateOllamaModel}
              className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs cursor-pointer transition-colors"
            >
              Set as Active Model
            </button>
          </div>
        )}

        <div className="pt-2">
          <button
            onClick={handleTestOllamaInference}
            disabled={testingOllama || !status?.online}
            className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer disabled:opacity-50 transition-colors"
          >
            {testingOllama ? (
              <>
                <span className="h-3 w-3 border-2 border-zinc-200 border-t-transparent rounded-full animate-spin"></span>
                Inferring...
              </>
            ) : (
              <>
                <Cpu className="h-3.5 w-3.5 text-emerald-400" />
                Run Local Health-Check Inference
              </>
            )}
          </button>
        </div>

        {ollamaTestResult && (
          <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-300 font-mono">
            {ollamaTestResult}
          </div>
        )}
      </div>

      {/* Pull Models Terminal Instructions */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/20 p-5 space-y-3">
        <h3 className="text-xs font-bold font-mono uppercase text-zinc-400">Download Local Open-Weight Models</h3>
        <p className="text-xs text-zinc-500">
          Run these in your terminal if you prefer zero-cloud local execution:
        </p>
        <div className="space-y-1.5 font-mono text-xs text-emerald-400 bg-zinc-950 p-3 rounded-lg border border-zinc-800">
          <div>ollama pull gemma4:e2b       # Gemma 4 lightweight local mentor</div>
          <div>ollama pull gemma2:2b       # General mentor (~1.6 GB)</div>
          <div>ollama pull nomic-embed-text  # Lightweight vector embeddings (~274 MB)</div>
        </div>
      </div>
    </div>
  );
}
