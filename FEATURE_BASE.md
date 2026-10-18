# 🚀 FirstPatch AI — Master Feature Base & Technical Specification

> **Mission:** "Don't just help developers write code. Help them understand, contribute, and grow as independent open-source developers."
> **Core Principle:** Deterministic tools establish facts. The local LLM explains those facts and guides the developer. The Reality Checker verifies claims before presenting them to the user.

---

## 1. System Architecture & Engineering Principle

FirstPatch AI solves the core engineering problem of **grounded generation over a codebase with a small local model** (Gemma 4 / Gemma 2 via Ollama):

```
GitHub URL -> Snapshot (SHA-Pinned) -> Code Index (AST/Symbols/Imports)
   -> Issue Fetch + Scoring -> Retrieval (Issue -> Code Candidates)
   -> Evidence Records -> Local LLM (Constrained JSON) -> Reality Checker
   -> Plan (VERIFIED / INFERRED / UNKNOWN) -> Tests Discovery -> PR Draft
```

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          FIRSTPATCH AI ARCHITECTURE                             │
├─────────────────────┬─────────────────────┬───────────────────┬─────────────────┤
│ 1. EVIDENCE LAYER   │ 2. CONSTRAINED LLM  │ 3. REALITY CHECK  │ 4. FLIGHT       │
│    (Deterministic)  │    (Local Gemma 4)  │    (Verification) │    RECORDER     │
│ • Python AST        │ • Structured JSON   │ • File existence  │ • Truthful PR   │
│ • SQLite FTS5       │ • Context budgeting │ • Exact lines     │ • Append-only   │
│ • SHA256 Hashes     │ • Tool contracts    │ • Excerpt compare │ • Step log      │
│ • Exact Line Bounds │ • Repair retry loop │ • Tri-state badge │ • Exportable    │
└─────────────────────┴─────────────────────┴───────────────────┴─────────────────┘
```

---

## 2. Master Feature Matrix

| Module | Feature | Implementation Mechanism | Status |
| :--- | :--- | :--- | :--- |
| **Onboarding** | Visual Contribution Sequence | 18-step interactive lifecycle guide (Discover $\rightarrow$ Fork $\rightarrow$ Branch $\rightarrow$ PR) | ✅ Active |
|  | Interactive Beginner Glossary | 30+ core open-source terms explained with repository context | ✅ Active |
|  | Progressive Disclosure UI | 3 explanation levels: Beginner, Intermediate, Advanced | ✅ Active |
| **Repository Intelligence** | SHA-Pinned Snapshots | Resolves default branch to exact commit SHA; pins all evidence | ✅ Active |
|  | Python AST Symbol Table | Extracts classes, methods, top-level functions, signatures, docstrings, exact lines | ✅ Active |
|  | Symbol-Based Chunking | Chunks code by functions/classes with SHA256 hashes (not fixed token windows) | ✅ Active |
|  | Architecture & Workflow Graph | Generates interactive Mermaid component maps and data flow diagrams | ✅ Active |
|  | Covered Domain Explorer | Identifies technical domains (AI/ML, Web, DevOps, Security) from manifests | ✅ Active |
| **Issue Intelligence** | Real Issue Ingestion | Fetches open GitHub issues, labels, comments, and milestones | ✅ Active |
|  | Issue Category Classifier | Classifies issues into Bug, Documentation, Testing, Feature, Refactoring | ✅ Active |
|  | Issue Claim-Safety Check | Scans assignees, linked PRs, and "I'll take this" comments to prevent wasted effort | ✅ Active |
|  | Transparent Suitability Scoring | Scores issues on clarity, scope, prerequisites, and test presence | ✅ Active |
|  | Stack Trace Parser | Regex-extracts file paths and line coordinates directly from error traces | ✅ Active |
| **Grounding & Reality Check** | Hybrid RAG (FTS5 + Vector) | Combines SQLite FTS5 lexical with `nomic-embed-text` embeddings via RRF | ✅ Active |
|  | Evidence Ledger | Persistent citations with commit-specific GitHub links (`#L{start}-L{end}`) | ✅ Active |
|  | Tri-State Fact Validation | Explicitly classifies claims as **`VERIFIED`**, **`INFERRED`**, or **`UNKNOWN`** | ✅ Active |
| **AI Mentorship & Runtimes** | Dual Mentorship Modes | **Learn Mode** (Socratic guidance & quizzes) vs. **Copilot Mode** (actionable diffs) | ✅ Active |
|  | Local Ollama Model Serving | High-throughput local inference with **`gemma4:e2b`** (72.4 tok/s) and Gemma 2 | ✅ Active |
|  | Cloud Scalability Support | Hybrid routing via **DigitalOcean Gradient™ AI Agentic Cloud** & GPU Droplets | ✅ Active |
| **Setup & Verification** | Setup Failure Doctor | Categorizes pip, npm, virtualenv, and env variable errors with safe shell fixes | ✅ Active |
|  | Sandboxed Test Execution | Runs test commands in restricted subprocesses; captures real exit codes | ✅ Active |
|  | PR Review Simulator | Audits unified diffs for leaked credentials, leftover `print()`, and missing tests | ✅ Active |
|  | Contribution Flight Recorder | Append-only event ledger generating maintainer-ready PR drafts with proof | ✅ Active |
| **Documentation Engine** | Auto-Generated Docs | Emits `PROJECT_OVERVIEW.md`, `ARCHITECTURE.md`, `BEGINNER_SETUP.md`, `CONTRIBUTION_GUIDE.md` | ✅ Active |

---

## 3. The 18-Step Beginner Contribution Lifecycle

FirstPatch AI breaks down open-source contribution into 18 verifiable milestones:

```
Phase 1: Discovery & Orientation
 1. Discover Project          -> Find and validate reputable repositories
 2. Read Project Overview     -> Understand core mission, dependencies, and entrypoints
 3. Understand Architecture   -> Inspect Mermaid component diagrams and data flow
 4. Read CONTRIBUTING.md      -> Verify branch conventions, PR template, DCO/CLA

Phase 2: Issue Selection
 5. Find Suitable Issue       -> Transparent suitability score based on clarity & tests
 6. Check Claim-Safety        -> Avoid duplicate work (scans assignees and active PRs)

Phase 3: Workspace Preparation
 7. Fork to Personal Account  -> Create remote copy without polluting upstream
 8. Create Working Branch     -> Conventional branch naming (e.g., `fix/issue-123`)
 9. Setup Environment         -> Install runtime dependencies, virtualenv, `.env`

Phase 4: Targeted Implementation
 10. Map Affected Code        -> AST symbol & stack trace matching with exact line bounds
 11. Design Minimal Fix       -> Socratic guidance keeping blast radius localized
 12. Implement Solution       -> Write clean, documented code following repository style

Phase 5: Quality & Verification
 13. Add / Update Tests       -> Write unit/integration tests for touched symbols
 14. Run Verification Suite   -> Run pytest/vitest in sandbox; record exit codes
 15. Review Proposed Diff     -> Pre-review check for secrets, debug code, lint errors

Phase 6: Submission & Collaboration
 16. Commit Changes           -> Conventional commit format (`fix(parser): handle empty strings`)
 17. Push & Open PR           -> Grounded PR draft with citations & verified test log
 18. Respond to Review        -> Address maintainer comments constructively
```

---

## 4. Grounded Evidence Ledger & Reality Checker

### Evidence Record Schema
Every factual claim is backed by an immutable SQLite record:

```json
{
  "id": "ev_031",
  "repository_id": "pallets/flask",
  "commit_sha": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
  "file_path": "src/flask/config.py",
  "start_line": 42,
  "end_line": 67,
  "symbol_name": "Config.from_prefixed_env",
  "chunk_type": "function",
  "content_hash": "sha256:7f83b165...",
  "match_type": "STACKTRACE",
  "source_url": "https://github.com/pallets/flask/blob/a1b2c3d4e5f6.../src/flask/config.py#L42-L67",
  "status": "VERIFIED"
}
```

### Tri-State Fact Classification
- **`VERIFIED`**: Claim is directly proven by deterministic checks (snapshot contains path, line range is valid, content hash matches, AST symbol exists at exact coordinates).
- **`INFERRED`**: Claim is a plausible deduction made by the model based on verified evidence (e.g., "this function likely causes the error because it parses the config key").
- **`UNKNOWN`**: Insufficient evidence in the repository snapshot to establish or refute the claim.
> **Rule:** An LLM judge can assist, but its verdict NEVER produces `VERIFIED`. Only deterministic code checks produce `VERIFIED`.

---

## 5. Local Model Serving & Empirical Benchmarks

FirstPatch AI defaults to **100% private, local inference** via Ollama on localhost:

### Benchmark Results (Empirical Performance on M-Series Mac)
| Model Tag | Parameters | Disk Size | Throughput | 3-Task Benchmark Pass Rate | Evaluation Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`gemma4:e2b`** (Primary) | ~2B (Efficient) | 7.5 GB | **72.4 tok/s** | **100.0% (3/3)** | 2.65s |
| **`qwen2.5-coder:3b`** | 3.1B | 1.9 GB | **37.7 tok/s** | **100.0% (3/3)** | 4.88s |
| **`gemma2:2b`** (Fallback) | 2.6B | 1.6 GB | **23.5 tok/s** | **66.7% (2/3)** | 8.12s |
| **`nomic-embed-text`** | 137M | 274 MB | Sub-millisecond | High retrieval precision | Embeddings |

### Benchmark Evaluation Suite (`POST /api/models/benchmark`)
Evaluates 3 real-world software engineering capabilities:
1. **AST Code Reasoning**: Interprets function contracts and returns bounded line locations.
2. **Constrained JSON Plan Generation**: Emits strictly validated JSON matching Pydantic schemas.
3. **Security Diff Review**: Detects hardcoded API keys (`ghp_...`, `AKIA...`) in git diffs.

---

## 6. Multi-Agent AI Orchestration Architecture

```
                    ┌───────────────────────────────┐
                    │       User / Issue Query      │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    1. Triage & Router Agent   │
                    │    (Intent & Stack Classify)  │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            Local Route (Default)           Cloud Route (Optional)
                    ▼                               ▼
        ┌─────────────────────────┐     ┌─────────────────────────┐
        │ 2. Reality Check Agent  │     │ DigitalOcean Gradient™  │
        │    (AST + Line Ranges)  │     │ Agentic Cloud Worker    │
        │    (Ollama gemma4:e2b)  │     │ (mlh.link/do-gradient)  │
        └────────────┬────────────┘     └────────────┬────────────┘
                     │                               │
                     └───────────────┬───────────────┘
                                     │
                                     ▼
                    ┌───────────────────────────────┐
                    │   3. Socratic Mentorship Agent│
                    │   (Learn vs. Copilot Mode)    │
                    └───────────────┬───────────────┘
                                     │
                                     ▼
                    ┌───────────────────────────────┐
                    │ 4. Verification & Review Agent│
                    │    (Sandbox + PR Draft)       │
                    └───────────────────────────────┘
```

---

## 7. Generated Documentation Specification

For every analyzed repository, FirstPatch AI generates markdown documentation at `docs/generated/`:

1. **`PROJECT_OVERVIEW.md`**: Project mission, architecture summary, entrypoints, directory hierarchy, and covered technical domains.
2. **`ARCHITECTURE.md`**: Mermaid component diagrams, module responsibilities, and request/response data flow.
3. **`BEGINNER_SETUP.md`**: Step-by-step local development setup, tool prerequisites, virtual environment, and test commands.
4. **`CONTRIBUTION_GUIDE.md`**: Repository contribution guidelines, branch conventions, PR checklist, and DCO/CLA requirements.
5. **`docs/generated/issues/ISSUE_<NUMBER>.md`**: Individual issue investigation reports with candidate files, evidence IDs, and claim-safety status.

---

## 8. Setup Failure Doctor & Secret Redaction

Deterministic regex signatures identify common onboarding failures and propose safe remediation commands:
- **Python**: `ModuleNotFoundError`, `ImportError`, virtualenv not activated, Python version mismatch.
- **Node.js**: `ERESOLVE` dependency conflicts, node-gyp build failures, unsupported Node engine.
- **Environment**: Missing `.env` file, unbound environment variables, port conflicts.
- **Safety**: Automatically redacts high-entropy strings, tokens (`ghp_`, `Bearer`, `sk-`), and passwords before any prompt or logging.

---

## 9. Security & Sandboxing Boundaries

- **SSRF Allowlist**: GitHub API and raw content domains only (`api.github.com`, `raw.githubusercontent.com`, `github.com`). Local/internal IPs are rejected.
- **Archive Path Traversal Protection**: Tarball extraction checks against `os.path.commonpath` / `..` traversal.
- **No Code Execution During Ingestion**: Repositories are analyzed statically via AST; no untrusted setup scripts are executed.
- **Isolated Verification Subprocesses**: User-approved test runs execute in restricted subprocesses with strict timeouts and resource bounds.
