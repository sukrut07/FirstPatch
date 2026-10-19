"use client";

import { useEffect, useState, useRef } from "react";
import { askMentor, listRepositories } from "@/lib/api";
import {
  Sparkles,
  Send,
  HelpCircle,
  Code,
  CheckCircle2,
  AlertCircle,
  FileCode,
  Layers,
  ChevronRight,
  BookOpen,
} from "lucide-react";

interface Message {
  sender: "user" | "mentor";
  content: string;
  evidence?: any[];
  model?: string;
  mode?: string;
  timestamp: string;
}

export default function MentorPage() {
  const [repos, setRepos] = useState<any[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [mode, setMentorMode] = useState<"learn" | "copilot">("learn");
  const [skillLevel, setSkillLevel] = useState<string>("Beginner");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRepositories().then((res) => {
      if (Array.isArray(res)) {
        setRepos(res);
        if (res.length > 0) {
          setSelectedRepo(res[0].id);
        }
      }
    });
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const presetQuestions = [
    "Where are the test suites located and how do I run them locally?",
    "Explain the top-level architecture and execution entrypoints.",
    "What are common setup pitfalls for new contributors in this repo?",
    "Which modules are easiest for a beginner to inspect first?",
  ];

  const handleAsk = async (textToAsk?: string) => {
    const q = textToAsk || question;
    if (!q.trim() || !selectedRepo) return;

    const userMsg: Message = {
      sender: "user",
      content: q.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToAsk) setQuestion("");
    setLoading(true);

    try {
      const res = await askMentor({
        repositoryId: selectedRepo,
        question: q.trim(),
        mode,
        skillLevel,
      });

      const mentorMsg: Message = {
        sender: "mentor",
        content: res.answer || "No response received.",
        evidence: res.evidence_used || [],
        model: res.model_used || "Gemma 4 / Grounded",
        mode,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, mentorMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        sender: "mentor",
        content: `Could not retrieve response: ${err.message}. Please verify the backend is running.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-xl bg-brand-50 border border-brand-200/80 flex items-center justify-center text-brand-600 shadow-sm">
              <Sparkles className="w-4 h-4" />
            </span>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Socratic AI Mentor</h1>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Grounded mentorship backed by real AST code symbols and test locations.
          </p>
        </div>

        {/* Repository Selector */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-gray-600">Context:</label>
          {repos.length > 0 ? (
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="input w-auto min-w-[200px] text-xs py-2"
            >
              {repos.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id} ({r.language || "Codebase"})
                </option>
              ))}
            </select>
          ) : (
            <span className="text-xs text-amber-700 bg-amber-50 px-3 py-1.5 rounded-xl border border-amber-200">
              No repositories indexed yet. Analyze one from Home first!
            </span>
          )}
        </div>
      </div>

      {/* Mode Switcher Banner */}
      <div className="card p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-gray-700">Mentorship Style:</span>
          <div className="flex items-center gap-1 bg-surface-100 p-1 rounded-2xl border border-gray-200/80">
            <button
              onClick={() => setMentorMode("learn")}
              className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                mode === "learn"
                  ? "bg-white text-brand-700 shadow-sm border border-brand-100"
                  : "text-gray-500 hover:text-gray-900"
              }`}
            >
              Learn Mode (Socratic &amp; Hints)
            </button>
            <button
              onClick={() => setMentorMode("copilot")}
              className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                mode === "copilot"
                  ? "bg-white text-brand-700 shadow-sm border border-brand-100"
                  : "text-gray-500 hover:text-gray-900"
              }`}
            >
              Copilot Mode (Direct Solutions)
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-gray-700">Experience:</span>
          <select
            value={skillLevel}
            onChange={(e) => setSkillLevel(e.target.value)}
            className="input w-auto text-xs py-1 px-3"
          >
            <option value="Beginner">Beginner</option>
            <option value="Intermediate">Intermediate</option>
            <option value="Advanced">Advanced</option>
          </select>
        </div>
      </div>

      {/* Main Chat Bento */}
      <div className="card p-6 flex flex-col min-h-[500px]">
        {/* Chat Messages Log */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2 mb-6">
          {messages.length === 0 ? (
            <div className="text-center py-12 space-y-4">
              <div className="w-12 h-12 rounded-3xl bg-brand-50 text-brand-600 flex items-center justify-center mx-auto shadow-sm">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-gray-900">
                Ask anything about {selectedRepo || "the codebase"}
              </h3>
              <p className="text-xs text-gray-500 max-w-md mx-auto">
                FirstPatch AI answers questions using AST-parsed file paths, symbols, and test suites. Select a question below to start:
              </p>

              {/* Presets */}
              <div className="flex flex-wrap gap-2 justify-center max-w-xl mx-auto pt-2">
                {presetQuestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleAsk(q)}
                    disabled={!selectedRepo || loading}
                    className="btn-secondary text-xs py-2 px-3.5 rounded-2xl text-left"
                  >
                    <ChevronRight className="w-3 h-3 text-brand-500 shrink-0 inline mr-1" />
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${m.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.sender === "mentor" && (
                  <div className="w-8 h-8 rounded-2xl bg-gradient-to-tr from-brand-600 to-purple-600 text-white flex items-center justify-center text-xs font-black shadow-sm shrink-0">
                    FP
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-3xl p-4 text-xs leading-relaxed ${
                    m.sender === "user"
                      ? "bg-brand-600 text-white shadow-md shadow-brand-500/20"
                      : "bg-surface-50 border border-gray-200/80 text-gray-800 shadow-sm"
                  }`}
                >
                  {m.sender === "mentor" && (
                    <div className="flex items-center justify-between mb-2 text-[10px] text-gray-400 font-mono">
                      <span>{m.model || "Gemma 4"}</span>
                      <span>{m.timestamp}</span>
                    </div>
                  )}
                  <div className="whitespace-pre-wrap">{m.content}</div>

                  {m.evidence && m.evidence.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-gray-200/60">
                      <p className="text-[10px] font-bold text-brand-700 uppercase tracking-wider mb-1">
                        CITED EVIDENCE ({m.evidence.length})
                      </p>
                      <div className="space-y-1">
                        {m.evidence.slice(0, 3).map((e: any, i: number) => (
                          <div key={i} className="font-mono text-[10px] text-gray-600 bg-white/70 p-1.5 rounded-lg border border-gray-200/60 truncate">
                            {e.file_path || e.symbol_name || "AST node reference"}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex gap-3 items-center text-xs text-gray-400">
              <div className="w-8 h-8 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center shrink-0">
                <Sparkles className="w-4 h-4 animate-spin" />
              </div>
              <span className="italic">Gemma 4 reasoning over codebase AST evidence…</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={`Ask a question about ${selectedRepo || "the repository"}…`}
            className="input flex-1 py-3 text-xs"
            disabled={loading || !selectedRepo}
          />
          <button
            type="submit"
            disabled={loading || !question.trim() || !selectedRepo}
            className="btn-primary py-3 px-5 rounded-2xl shrink-0"
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline">Ask Mentor</span>
          </button>
        </form>
      </div>
    </div>
  );
}
