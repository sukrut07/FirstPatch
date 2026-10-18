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

## Phase 3: Isolated Test Execution & Contribution Verification (Completed)

| Component | Status | Notes |
|---|---|---|
| **Independent Verification Service** | ✅ Done | `IsolatedVerificationService` with async semaphore concurrency limiter (max 3) |
| **Strict Security Boundaries** | ✅ Done | Non-root (`1000:1000`), `--network none`, `--read-only`, tmpfs `/tmp`, CPU/RAM/PID limits, `--cap-drop ALL`, no socket mounts |
| **Zero Host Execution Rule** | ✅ Done | Prohibits host fallback; reports `UNAVAILABLE` when safe container infrastructure is absent |
| **Verification State Machine** | ✅ Done | 10 explicit states (`QUEUED`, `PREPARING`, `RUNNING`, `PASSED`, `FAILED`, `TIMED_OUT`, `BLOCKED`, `UNSUPPORTED`, `UNAVAILABLE`, `CANCELLED`) |
| **Commit SHA Evidence Binding** | ✅ Done | Verified records bound to snapshot commit SHA; stale commit detection via `VerificationRealityAdapter` |
| **Allowlisted Project Types** | ✅ Done | Python (`python_pytest` via `python:3.11-slim`), Node.js/TypeScript (`node_jest` / `node_npm_test` via `node:20-slim`) |
| **Accurate Output Parsers** | ✅ Done | `PytestOutputParser` and `JestNpmOutputParser` extracting exact test counts without fabrication |
| **Bounded Logs & Cleanup** | ✅ Done | Stdout/stderr capped at 50KB; unconditional workspace and container cleanup in `finally` blocks |
| **API Endpoints** | ✅ Done | `/api/verification/health`, `/api/verification/run`, `/api/verification/runs/{run_id}`, `/api/verification/runs/{run_id}/cancel`, `/api/verification/{session_id}` |
| **Frontend UI Panel** | ✅ Done | `VerificationPanel` embedded in Overview and Plan views with live status, counts, bounded logs, and diagnostics |

---

## Phase 4: Dataset Intelligence, Gemma Adaptation & Benchmark Evaluation (Completed & Audited)

| Component | Status | Notes |
|---|---|---|
| **Dataset Manifest** | ✅ Done (Audited) | 14 sources registered covering all 12 candidate datasets + synthetic set with URLs, licenses, sizes, and governance decisions |
| **Acquisition & Consent Gating** | ✅ Done (Audited) | `DatasetPipeline.acquire()` enforces explicit approval constraint; step-by-step acquisition instructions |
| **Synthetic Evaluation Set** | ✅ Done (Audited) | Deterministic synthetic set with base commit SHAs, URLs, licenses, and zero external dependencies |
| **JSONL Pipeline & Split Isolation** | ✅ Done (Audited) | `create_repository_splits()` partitions tasks strictly at the repository level to guarantee zero cross-split leakage |
| **Dataset Validator & Secret Filtering** | ✅ Done (Audited) | Validates JSON/schema integrity, rejects GitHub PATs, Google AI keys, AWS keys, private keys, bearer tokens, and path traversal |
| **Task Schema with Provenance** | ✅ Done (Audited) | `EvaluationTask` records `commit_sha`, `source_url`, `dataset_version`, `license`, `split`; `TaskResult` records `evaluation_mode` |
| **Rigorously Verified Metrics** | ✅ Done (Audited) | P, R, F1, Recall@k, Hit@k, MRR, MAP, Evidence-Validity Rate, Unsupported-Claim Rate, and False Verification-Pass Rate |
| **Evaluator & Mode Separation** | ✅ Done (Audited) | Explicit separation of `DETERMINISTIC_BASELINE`, `LIVE_AI`, and `MOCK_AI` modes; honest reporting without false AI claims |
| **Atomic Benchmark Result Store** | ✅ Done (Audited) | Atomic temporary-file-and-rename writes; `offset` pagination; workspace-safe directory layout |
| **Dataset & Benchmark APIs** | ✅ Done (Audited) | Path traversal protection (`_validate_safe_source_name`), `asyncio.Lock` concurrency guard, input bounds ($\le 500$) |
| **Phase 4 Quality Gate Audit Suite** | ✅ Done (Audited) | 98 tests (76 initial + 22 quality gate audit tests) covering metrics, security, mode separation, and full E2E workflow |

---

## Master Implementation: Proof-Carrying Contributions & Contribution Trust Layer (Completed)

| Component | Status | Notes |
|---|---|---|
| **Fact Store** | ✅ Done | SQLite parameterized storage bound to repository and commit SHA; safe path normalizer (`normalize_repo_path`) |
| **Claim Models** | ✅ Done | Untrusted proposer `Claim` models strictly lacking any self-certifying verdict field; deterministic `Verdict` schema |
| **Deterministic Checker Kernel** | ✅ Done | Dispatches claims to registered checkers (`FILE_EXISTS`, `SYMBOL_IN_FILE`, `LINES_CONTAIN`, `IMPORTED_BY`, `TEST_IMPORTS`, `POLICY_FACT`, `ISSUE_UNCLAIMED`, `VERIFY_RESULT`, `REVIEW_THEME_SUPPORTED`); catches exceptions as `UNKNOWN` |
| **Trusted Renderer** | ✅ Done | Separates verified statements from raw untrusted model prose into an explicit `unverified explanation` section |
| **Contribution Policy Radar** | ✅ Done | Detects AI bans, disclosure rules, issue assignment constraints; switches to Learn Mode when AI is prohibited |
| **Issue Claim & Duplicate-PR Guard** | ✅ Done | Detects assigned issues, linked open PRs, and comment claims with evidence tracking and bounded caching |
| **Contributor Understanding Gate** | ✅ Done | Synthesizes 3 comprehension questions strictly from verified claims; evaluates grounded answers deterministically |
| **Tamper-Evident Flight Receipt** | ✅ Done | SHA-256 canonical hash-chained event recorder tracking step sequence and driver provenance; verification endpoint |
| **Repository Review Memory** | ✅ Done | Ingests bounded review comment samples; extracts recurring themes with a minimum 2-comment threshold |
| **Blast Radius & Impact Analysis** | ✅ Done | AST import and test dependency tracing with high-confidence vs regex fallback labeling and qualitative risk notes |
| **Abstention Decision Engine** | ✅ Done | Refuses unsupported recommendations when score margins or evidence counts are low; risk-coverage evaluation |
| **Kernel Mutation Testing & Canary** | ✅ Done | 12+ adversarial mutations testing catch rate (100%) and false rejection rate (0.0%); prompt-injection canary tests |
| **Trust API Endpoints** | ✅ Done | Complete REST endpoints mounted at `/api/trust/*` |

---

## Verified Test & Build Results

```
Backend pytest:  275 passed, 0 failed in 1.61s (100% pass rate across Phases 0-4 + Master Implementation)
Lint (ruff):     All checks passed!
Security:        Prompt-injection canary tested, path traversal rejected, mock-driver escalation prevented
Frontend:        0 files modified (100% untouched)
```


