# FirstPatch AI — Architecture Overview

FirstPatch AI is organized as a modular, local-first system designed for zero-code hallucination, high performance, and safe developer onboarding.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Next.js 16 Frontend                           │
│  - App Router, React 19, TypeScript, Tailwind CSS, Lucide Icons       │
│  - Live Ollama Connectivity Status                                     │
│  - Interactive AST Symbol & Evidence Viewer                            │
│  - Socratic Learn Mode vs. Implementation Copilot Mode                 │
│  - Contribution Flight Recorder & PR Review Simulator                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST API (Typed Client)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend Engine                         │
│  - Pydantic Settings & Request Validation                              │
│  - Routers: repositories, issues, retrieval, mentor, contributions,    │
│    verification, review, learning, health                              │
└──────┬────────────────────┬────────────────────┬───────────────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────┐   ┌─────────────────┐   ┌───────────────────────────────┐
│  GitHub API  │   │ Deterministic   │   │ Local Ollama Service          │
│  & Git Client│   │ Code Parser     │   │ - gemma2:2b (mentor chat)     │
│  - Bounded   │   │ - Python AST    │   │ - nomic-embed-text (vectors)  │
│    manifest  │   │ - Regex symbols │   │ - Low temp (0.1) for facts    │
│  - File tree │   │ - Chunk hash    │   │ - Strict context budgeting    │
└──────────────┘   └─────────────────┘   └───────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Local SQLite Database (WAL)                      │
│  - repositories, repository_snapshots, repository_files                │
│  - code_chunks & code_chunks_fts (FTS5 Lexical Index)                  │
│  - symbols, issues, issue_recommendations                              │
│  - contribution_workspaces, steps, flight_recorder_events              │
│  - verification_runs, review_findings, learning_profiles               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Deterministic Extraction Pipeline

To eliminate model hallucinations, the backend never asks the LLM to invent repository structure. Instead:
1. **GitHub Ingestion:** Fetches bounded file trees and key files (`README.md`, `pyproject.toml`, `package.json`, test files).
2. **AST Analysis (`ast_service.py`):** Uses Python's native `ast` module to extract classes, class methods, top-level functions, arguments, docstrings, and start/end line coordinates.
3. **Symbol Table & Chunking (`chunking_service.py`):** Splits files into logical units with exact start/end line numbers and computes a SHA256 content hash for cache verification.
4. **FTS5 Indexing (`database.py`):** Inserts chunks into an SQLite FTS5 full-text index for sub-millisecond keyword retrieval.

---

## 2. Hybrid Retrieval-Augmented Generation (RAG)

When a developer asks a question or requests an issue contribution plan:
1. **Lexical Search:** Queries SQLite FTS5 for exact symbol names, module imports, error messages, or function names.
2. **Vector Similarity:** Obtains query embeddings from `nomic-embed-text` via Ollama and computes cosine similarity against stored chunk embeddings.
3. **Reciprocal Rank Fusion (RRF):** Combines lexical and semantic ranks:
   $$\text{RRF Score} = \frac{1}{60 + \text{Rank}_{\text{lexical}}} + \frac{1}{60 + \text{Rank}_{\text{vector}}}$$
4. **Context Budget Assembler:** Selects top chunks within a bounded token budget ($\le 24,000$ characters) and appends stable GitHub permalinks (`#L{start}-L{end}`).

---

## 3. Sandboxed Verification Engine

1. **Subprocess Isolation:** Commands are executed inside bounded child processes with strict timeouts ($\le 60$s) and working directory boundaries.
2. **Token Blacklist:** Commands containing destructive patterns (`rm -rf`, `sudo`, `dd`, `mkfs`, `/dev/`, chain injections) are blocked deterministically.
3. **Evidence Persistence:** Exit codes, stdout, and stderr are stored in the database. A test is only marked `PASSED` if its exit code is strictly `0`.

---

## 4. Contribution Flight Recorder

Logs each user milestone into an append-only timeline table (`flight_recorder_events`):
- `REPO_ANALYZED`
- `PLAN_CREATED`
- `STEP_COMPLETED`
- `TEST_RUN`
- `REVIEW_CONDUCTED`
- `PR_DRAFTED`

The PR draft generator aggregates these real events to produce a truthful PR body containing exact test outputs and a maintainer checklist.
