"use client";

import { useEffect, useState } from "react";
import { listRepositories, askMentor } from "@/lib/api";
import { 
  Sparkles, 
  Send, 
  ExternalLink, 
  BookOpen, 
  Terminal, 
  Layers, 
  CheckCircle,
  HelpCircle
} from "lucide-react";

export default function MentorPage() {
  const [repos, setRepos] = useState<any[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [mode, setMode] = useState<"learn" | "copilot">("learn");
  const [skillLevel, setSkillLevel] = useState<string>("Beginner");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listRepositories().then((list) => {
      setRepos(list);
      if (list.length > 0) {
        setSelectedRepo(list[0].id);
      }
    });
  }, []);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading || !selectedRepo) return;

    const userText = input;
    setInput("");
    setLoading(true);

    const newMsgs = [...messages, { role: "user", content: userText }];
    setMessages(newMsgs);

    try {
      const res = await askMentor({
        repositoryId: selectedRepo,
        question: userText,
        mode: mode,
        skillLevel: skillLevel
      });
      setMessages([...newMsgs, {
        role: "assistant",
        content: res.answer,
        evidence: res.evidence,
        model: res.model_used
      }]);
    } catch (err: any) {
      setMessages([...newMsgs, {
        role: "assistant",
        content: `Error: ${err.message}`
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Header & Settings */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-medium mb-1.5">
            <Sparkles className="h-3 w-3" />
            <span>AI Codebase Mentor</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-zinc-100">Interactive Open-Source Mentorship</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Grounds all pedagogical explanations in real repository AST files and test suites.
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Repo Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-400">Target Repo:</span>
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="bg-zinc-900 border border-zinc-800 text-xs text-zinc-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500"
            >
              {repos.map((r) => (
                <option key={r.id} value={r.id}>{r.id}</option>
              ))}
            </select>
          </div>

          {/* Mode Selector */}
          <div className="flex items-center bg-zinc-900 p-1 rounded-lg border border-zinc-800">
            <button
              onClick={() => setMode("learn")}
              className={`px-3 py-1 rounded text-xs font-medium cursor-pointer transition-colors ${
                mode === "learn"
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Learn Mode
            </button>
            <button
              onClick={() => setMode("copilot")}
              className={`px-3 py-1 rounded text-xs font-medium cursor-pointer transition-colors ${
                mode === "copilot"
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Copilot Mode
            </button>
          </div>
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-4">
        {/* Messages Scroll Area */}
        <div className="space-y-4 min-h-[420px] max-h-[600px] overflow-y-auto p-4 rounded-xl bg-zinc-950/70 border border-zinc-800/80">
          {messages.length === 0 ? (
            <div className="text-center py-24 space-y-3">
              <div className="h-10 w-10 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto">
                <Sparkles className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold text-zinc-200">
                {mode === "learn" ? "Learn Mode Active" : "Copilot Mode Active"}
              </h3>
              <p className="text-xs text-zinc-500 max-w-md mx-auto">
                {mode === "learn"
                  ? "Ask how any module, class, or test fixture works. The mentor will provide plain-language concepts, code line walkthroughs, and a quick knowledge check."
                  : "Ask for concrete implementation guidance, code patches, or test-to-target execution commands for your active issue."}
              </p>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-xl text-xs space-y-2 leading-relaxed ${
                  m.role === "user"
                    ? "bg-zinc-900 border border-zinc-800 text-zinc-200 ml-auto max-w-xl"
                    : "bg-zinc-950 border border-zinc-800 text-zinc-300 max-w-3xl"
                }`}
              >
                <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono mb-1">
                  <span>{m.role === "user" ? "You" : `FirstPatch Mentor (${m.model || 'Gemma 2'})`}</span>
                </div>
                <div className="whitespace-pre-wrap">{m.content}</div>

                {m.evidence?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-zinc-800/80">
                    <span className="text-[10px] font-mono text-emerald-400 block mb-1">GROUNDED CODE REFERENCES:</span>
                    <div className="space-y-1">
                      {m.evidence.map((ev: any) => (
                        <div key={ev.id} className="text-[11px] font-mono text-zinc-400 flex items-center justify-between">
                          <span>• {ev.file_path} (L{ev.start_line}-L{ev.end_line})</span>
                          <a href={ev.source_url} target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline flex items-center gap-1">
                            GitHub Line <ExternalLink className="h-2.5 w-2.5" />
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            type="text"
            placeholder={
              mode === "learn"
                ? "Ask a conceptual question (e.g. Explain how tests in this repository are structured)..."
                : "Ask for code fix recommendations (e.g. How do I fix the configuration KeyError)..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 p-3 rounded-lg border border-zinc-800 bg-zinc-950 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-3 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50 shrink-0"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 border-2 border-zinc-950 border-t-transparent rounded-full animate-spin"></span>
                Reasoning...
              </>
            ) : (
              <>
                <Send className="h-3.5 w-3.5" />
                Ask Mentor
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
