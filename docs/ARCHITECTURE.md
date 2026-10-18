# FirstPatch AI — Architecture Overview & Trust Layer Specification

FirstPatch AI is an evidence-backed open-source contribution mentor combining a local-first AST pipeline, an untrusted proposer abstraction (Gemma / LLM), deterministic reality verification, and a tamper-evident Contribution Flight Recorder.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Next.js 16 Frontend (Turbopack, React 19)            │
│  - Recharts Diagrammatic Codebase Analysis (AST density, Fit Radar)    │
│  - Interactive AST Symbol & Evidence Ledger Viewer                     │
│  - Socratic Learn Mode vs. Implementation Copilot Mode                 │
│  - Custom Cloud API Key Drawer & Local Ollama Zero-Cost Mode           │
│  - Contribution Flight Recorder & PR Review Simulator                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST API (Typed Client)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend Engine                          │
│  - Routers: repositories, issues, retrieval, mentor, contributions,    │
│    verification, review, learning, compliance, trust, benchmark        │
└──────┬────────────────────┬────────────────────┬───────────────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────┐   ┌─────────────────┐   ┌───────────────────────────────┐
       │                    │                    │
┌──────────────┐   ┌─────────────────┐   ┌───────────────────────────────┐
│  GitHub API  │   │ Deterministic   │   │ Local Ollama (Gemma 4 / 2)    │
│  & Git Client│   │ Code Parser     │   │ Cloud LLM (OpenAI / Gradient) │
│  - Bounded   │   │ - Python AST    │   │ - Grounded context injection  │
│    manifest  │   │ - Regex symbols │   │ - Low temp (0.1) for facts    │
│  - File tree │   │ - Chunk hash    │   │ - Strict token budgeting      │
└──────────────┘   └─────────────────┘   └───────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Local SQLite Database (WAL)                       │
│  - repositories, repository_snapshots, repository_files                │
│  - code_chunks & code_chunks_fts (FTS5 Lexical Index)                  │
│  - symbols, issues, issue_recommendations, issue_triages               │
│  - contribution_workspaces, steps, flight_recorder_events              │
│  - verification_runs, review_findings, learning_profiles               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Deterministic Code Ingestion & AST Parsing

To eliminate model hallucinations, the backend never asks the LLM to invent repository structure:
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

## 3. Proof-Carrying Contributions & Contribution Trust Layer

FirstPatch AI implements a deterministic trust boundary separating untrusted proposers (LLM / Gemma / heuristics) from deterministic verification:

```text
Repository Snapshot + Commit SHA
              │
              ▼
      FACT STORE / INDEX
              │
              ▼
       UNTRUSTED PROPOSER (Gemma / AI)
              │
       Structured Claims (no verdict fields)
              │
              ▼
      DETERMINISTIC KERNEL
              │
      VERIFIED / REFUTED / STALE / UNKNOWN
              │
              ▼
       TRUSTED RENDERER
              │
              ▼
      RECEIPT / PR PACKAGE
```

### Core Trust Subsystems
1. **Fact Store (`app/services/trust/fact_store.py`)**: SQLite parameterized persistence keyed to repository and commit SHA. Enforces strict path normalization (`normalize_repo_path`) to eliminate path traversal, absolute drives, and null bytes.
2. **Untrusted Claim Models (`app/services/trust/claims.py`)**: Proposers create `Claim` objects without the ability to self-certify an assertion as verified.
3. **Deterministic Checker Kernel (`app/services/trust/kernel.py`, `checkers.py`)**: Dispatches claims against immutable facts. Enforces SHA matching (stale detection) and emits signed `Verdict` objects.
4. **Trusted Renderer (`app/services/trust/render.py`)**: Assembles verified plan steps from checked arguments while strictly isolating raw model prose.
5. **Contribution Policy Radar (`app/services/policy_radar/service.py`)**: Scans `CONTRIBUTING.*`, AI policy files, and PR templates. Flags AI bans and requires disclosures.
6. **Issue Claim & Duplicate-PR Guard (`app/services/claim_guard/service.py`)**: Detects assigned issues, linked open PRs, and comment claims to prevent duplicate contributor effort.
7. **Contributor Understanding Gate (`app/services/understanding_gate/service.py`)**: Synthesizes 3 comprehension questions strictly from verified claims, evaluating answers deterministically without blocking users.
8. **Tamper-Evident Contribution Receipt (`app/services/trust/receipt.py`)**: SHA-256 canonical hash-chained flight recorder tracking the contribution lifecycle with verification driver provenance.
9. **Repository Review Memory (`app/services/trust/review_memory.py`)**: Analyzes sampled PR review comments for recurring maintainer expectations.
10. **Blast Radius & Impact Analysis (`app/services/trust/blast_radius.py`)**: Traces AST dependencies and test targets to produce qualitative risk notes.

---

## 4. Sandboxed Verification & Setup Failure Doctor

1. **Subprocess Isolation:** Commands are executed inside bounded child processes with strict timeouts ($\le 60$s) and working directory boundaries.
2. **Token Blacklist:** Commands containing destructive patterns (`rm -rf`, `sudo`, `dd`, `mkfs`, `/dev/`, chain injections) are blocked deterministically.
3. **Evidence Persistence:** Exit codes, stdout, and stderr are stored in the database. A test is only marked `PASSED` if its exit code is strictly `0`.
4. **Setup Failure Doctor (`setup_doctor_service.py`):** Deterministic regex classifiers for `ModuleNotFoundError`, `ERESOLVE`, port collisions, missing `.env` variables with copyable safe fixes.

---

## 5. Contribution Flight Recorder

Logs each user milestone into an append-only timeline table (`flight_recorder_events`):
- `REPO_ANALYZED`
- `PLAN_CREATED`
- `STEP_COMPLETED`
- `TEST_RUN`
- `REVIEW_CONDUCTED`
- `PR_DRAFTED`

The PR draft generator aggregates these real events to produce a truthful PR body containing exact test outputs, maintainer checklists, and evidence receipts.
