# FirstPatch AI — Feature Implementation Status

This document reflects the verified implementation state of the FirstPatch AI platform.

| Feature Area | Sub-Feature | Status | Verification Details |
| :--- | :--- | :--- | :--- |
| **Repository Ingestion** | GitHub REST API Client | ✅ Implemented & Tested | Bounded tree extraction, rate limit handling |
|  | AST Symbol Parsing | ✅ Implemented & Tested | Classes, methods, functions, line coordinates (`ast_service.py`) |
|  | Content Chunking & Hashing | ✅ Implemented & Tested | SHA256 chunk hashing, exact line coordinates |
|  | SQLite FTS5 Lexical Search | ✅ Implemented & Tested | Sub-millisecond full-text chunk queries |
| **Local AI & RAG** | Ollama Model Integration | ✅ Implemented & Tested | `gemma2:2b`, `qwen2.5-coder:3b`, `nomic-embed-text` |
|  | Hybrid RAG (Lexical + Vector) | ✅ Implemented & Tested | RRF combination with fallback when offline |
|  | Evidence Ledger Citations | ✅ Implemented & Tested | Stable line-range URLs (`#L{start}-L{end}`) |
| **Issue Intelligence** | Issue Retrieval & Filtering | ✅ Implemented & Tested | Excludes PRs, fetches labels and comments |
|  | Transparent Scoring Heuristics | ✅ Implemented & Tested | Scores on labels, clarity, size, and prerequisites |
|  | Prerequisite Detection | ✅ Implemented & Tested | Detects required tools (pytest, async, etc.) |
| **Mentorship** | Learn Mode (Socratic) | ✅ Implemented & Tested | Explains concepts, concepts-first guidance |
|  | Copilot Mode (Plan & Patch) | ✅ Implemented & Tested | Step-by-step contribution plan generation |
| **Setup & Health** | Setup Failure Doctor | ✅ Implemented & Tested | Classifies pip, npm, env, and port errors |
| **Verification & PR** | Safe Subprocess Sandbox | ✅ Implemented & Tested | Captures exit codes, stdout/stderr, blocks dangerous tokens |
|  | Flight Recorder Timeline | ✅ Implemented & Tested | Logs journey events into SQLite |
|  | PR Review Simulator | ✅ Implemented & Tested | Audits unified diffs for secrets, logs, tests |
|  | Truthful PR Draft Generator | ✅ Implemented & Tested | Drafts PR with actual test outputs and checklist |
| **User Interface** | Next.js 16 App Router UI | ✅ Implemented & Tested | Responsive dark-first theme, Lucide icons |
|  | Interactive Repository Dashboard | ✅ Implemented & Tested | Tabs for Overview, Files, Architecture, Issues, Doctor, Mentor |
|  | Model Management & Status Pill | ✅ Implemented & Tested | Live Ollama connectivity indicator |
