# FirstPatch AI — Implementation Plan

## Phase 0: Foundation (Completed)

| Component | Status | Notes |
|---|---|---|
| Project monorepo structure | ✅ Done | `frontend/` + `backend/` + `docs/` |
| Backend FastAPI app | ✅ Done | With lifespan, CORS, routing |
| Pydantic v2 schemas | ✅ Done | Full API contract defined |
| SQLite persistence | ✅ Done | repository_cache, sessions, issue_cache |
| GitHub service | ✅ Done | SSRF protection, rate limit handling |
| Repository analysis service | ✅ Done | Framework/config/test detection |
| Issue matching engine (7-criterion deterministic) | ✅ Done | Transparent scoring |
| Documentation & environment config | ✅ Done | README, ARCH, API, SECURITY, PLAN |

---

## Phase 1: Backend Intelligence, Gemma Integration & Agent Orchestration (Completed)

| Component | Status | Notes |
|---|---|---|
| **Gemma 4 AI Provider Adapter** | ✅ Done | `gemma-4-31b-it` via Google AI Studio API and Ollama (`gemma3:12b`); structured JSON parsing & repair |
| **Deterministic AI Fallback** | ✅ Done | Honest `is_fallback: True` reporting; no false claims of AI invocation |
| **Python AST Analysis** | ✅ Done | Classes, methods, functions, imports, decorators, precise line ranges via `ast.parse` |
| **Multi-Language Structure Heuristics** | ✅ Done | JavaScript/TypeScript, Go, Rust with explicit limitation disclosures |
| **Controlled Agent Orchestrator** | ✅ Done | Stages 1-8 pipeline coordinating Tools A through H |
| **Agent Tools (Tools A through H)** | ✅ Done | `inspect_repository`, `analyze_code_structure`, `fetch_open_issues`, `rank_contribution_issues`, `build_evidence_bundle`, `generate_contribution_plan`, `diagnose_setup_error`, `validate_plan_evidence` |
| **Repository Reality Checker** | ✅ Done | Validates claims, flags hallucinated files, unknown evidence IDs, commit mismatches, unsupported test claims; bounded plan repair |
| **Setup Failure Doctor** | ✅ Done | Pattern matching for Python venv, missing modules, Node ERESOLVE/build, missing env vars, port conflicts, pytest collection; zero command execution |
| **Test Suite** | ✅ Done | 67 / 67 tests passing across unit, integration, reality checking, security, and orchestrator workflows |
| **Frontend Verification** | ✅ Done | TypeScript 0 errors, ESLint 0 errors, Next.js production build clean |

---

## Phase 2: Sandboxed Verification & PR Automation (Next)

### High Priority
1. **Isolated Sandboxed Test Execution**
   - Docker container execution with bounded CPU, memory, timeout, and read-only source mounts.
   - Capture test execution stdout/stderr safely to verify proposed bug fixes.

2. **Database Caching with TTL & Freshness Detection**
   - Wire `RepositoryCache` and `IssueCache` ORM models to live requests.
   - Detect stale cache when `commit_sha` advances on the remote repository.

3. **Interactive Contributor Flight Recorder**
   - Step-by-step progress checklist in frontend UI.
   - Record time spent and concepts learned.

### Medium Priority
4. **Pull Request Preparation Assistant**
   - Interactive PR template generator linking fixed issue numbers.
   - Git diff preview and commit message linting.

5. **Multi-language Semantic Vector Search**
   - Embeddings for large codebase semantic navigation when repository exceeds bounded file limits.

---

## Verified Test & Build Results

```
Backend pytest:  67 passed in 1.02s (100% pass rate)
Frontend lint:   0 warnings, 0 errors
TypeScript:      npx tsc --noEmit clean (0 errors)
Next.js build:   npm run build clean (compiled successfully)
```
