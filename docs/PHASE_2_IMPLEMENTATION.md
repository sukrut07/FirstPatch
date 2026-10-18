# FirstPatch AI — Phase 2 Implementation Guide

## Parallel Development: Repository Intelligence, Evidence Grounding & Issue-to-Code Mapping

This document details the architecture, module ownership, deterministic validation rules, security boundaries, and integration contracts implemented in Phase 2 of FirstPatch AI.

---

### 1. Phase Boundary and Ownership Audit

#### Existing & Reusable Services (Reused as-is)
- `app.services.github.client.GitHubService`: URL normalization, SSRF protection (`_ALLOWED_GITHUB_HOST`), metadata retrieval, commit SHA retrieval, tree retrieval, issues retrieval, languages, bounded content fetching.
- `app.schemas.models`: `EvidenceRef`, `EvidenceStatus`, `EvidenceType`, `GitHubIssue`, `MatchedIssue`, `IssueMatchCriterion`, `RepositoryOverview`.
- `app.services.issue_matching.engine`: 7-criterion deterministic readiness scoring model (`issue_is_open`, `has_clear_description`, `not_stale`, `has_reproduction_or_steps`, `has_good_first_issue_label`, `language_match`, `has_tests_nearby`).
- `app.core.config`, `app.core.logging`, `app.db.database`.

#### Phase 2 Responsibilities (Fully Implemented)
- **Pinned Repository Snapshots & Inventory**: `app.services.repository_intelligence.snapshot.RepositorySnapshotService`
- **Source-Code Structural Analysis**: `app.services.repository_intelligence.code_structure.CodeStructureAnalyzer` (Python AST, JS/TS pattern parsing, generic fallback)
- **Deterministic Evidence Validation & Reality Checking**: `app.services.repository_intelligence.evidence_validator.EvidenceValidator`
- **Evidence Extraction**: `app.services.repository_intelligence.evidence_extractor.EvidenceExtractor`
- **Real Issue-to-Code Mapping**: `app.services.repository_intelligence.issue_mapper.IssueToCodeMapper`
- **Contribution Plan Preparation & Validation**: `app.services.repository_intelligence.contribution_plan.ContributionPlanService` & `PlanValidator`
- **Static Test Discovery**: `app.services.repository_intelligence.test_discovery.TestDiscoveryService`
- **Security Boundaries & Redaction**: `app.services.repository_intelligence.security`
- **Phase 1 Integration Contract**: `app.services.repository_intelligence.service.RepositoryIntelligenceService`

#### Phase 1 Dependencies (Owned by Phase 1 Teammate)
- Gemma model integration (`google_ai_studio`, `local_ollama`)
- Agent orchestrator and multi-turn conversational loop
- Global application router mounting for production endpoints
- User profile / preferences persistence

---

### 2. Module Structure

```text
backend/app/services/repository_intelligence/
├── __init__.py                # Package exports and public symbols
├── exceptions.py              # Domain exceptions (SnapshotIncompleteError, StaleSnapshotError, etc.)
├── schemas.py                 # Typed Pydantic v2 schemas for Phase 2
├── security.py                # Credential redaction, path traversal sanitizer
├── snapshot.py                # RepositorySnapshotService (pinned commit SHA & file inventory)
├── code_structure.py          # CodeStructureAnalyzer (Python AST & JS/TS structural parsing)
├── evidence_extractor.py      # Generates EvidenceRef and ClaimRecord from symbols/files
├── evidence_validator.py      # EvidenceValidator (Deterministic Repository Reality Checker)
├── issue_mapper.py            # IssueToCodeMapper (Symbol/file mapping + 7-criterion scoring)
├── contribution_plan.py       # ContributionPlanService & PlanValidator (6-stage plans)
├── test_discovery.py          # TestDiscoveryService (Static test configuration discovery)
└── service.py                 # RepositoryIntelligenceService (Phase 1 Integration Contract facade)
```

---

### 3. Repository Snapshot & Inventory Strategy

1. **Validation & SSRF Protection**: The URL is normalized and restricted to `github.com`. Private IPs and localhost are rejected.
2. **Commit SHA Pinning**: The analysis resolves the default branch HEAD commit SHA (or accepts an explicit commit SHA). All subsequent file content and evidence references are pinned to this SHA.
3. **Tree & Inventory**: Fetches the Git tree, validates all paths against path-traversal attacks, and classifies files into `SOURCE`, `TEST`, `CONFIG`, `MANIFEST`, `DOC`, `ASSET`, or `OTHER`.
4. **Manifest & Test Configuration Tracking**: Detects package manifests (`requirements.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`) and test configurations (`pytest.ini`, `jest.config.*`, `vitest.config.*`, etc.).
5. **Bounded Content Retrieval with Caching**: Fetches file contents with in-memory caching keyed by `(owner, repo, sha:path)` to prevent redundant API calls.
6. **Honesty on Partial Failures**: If the tree is truncated or cannot be resolved, `is_partial = True` and explicit warnings are recorded. If no commit SHA can be determined, `SnapshotIncompleteError` is raised.

---

### 4. Source-Code Structural Analysis

- **Python**:
  - Uses the standard library `ast` module.
  - Extracts `FunctionDef` and `AsyncFunctionDef` with line ranges, docstrings, parameters, and decorators.
  - Identifies web routes (FastAPI/Flask/Django decorators such as `@router.get`, `@app.post`).
  - Identifies test functions (`test_*`) and test classes (`Test*`).
  - Extracts imports (`import x`, `from x import y as z`).
  - Syntax errors in repository files are captured gracefully in `parse_errors` without crashing the service.
- **JavaScript & TypeScript**:
  - Extracts functions (`function name(...)`, `const name = (...) =>`), classes, imports, routes (`app.get(`, `router.post(`), and test cases (`describe`, `it`, `test`).
- **Generic Fallback**:
  - Extracts functions, classes, and types for Go, Rust, Java, and other languages.
- **Filters**: Generated code (`dist/`, `build/`, `node_modules/`, `*.min.js`, `*.pyc`) is automatically excluded.

---

### 5. Evidence Validation & Repository Reality Checker

Every factual claim about repository code must pass deterministic validation:

| Status | Deterministic Validation Rules |
|---|---|
| `VERIFIED` | (1) Referenced file exists in pinned snapshot.<br>(2) Line range is valid ($1 \le \text{start\_line} \le \text{end\_line} \le \text{total\_lines}$).<br>(3) Excerpt matches the actual file content at those lines.<br>(4) Source code at those lines mentions the key terms claimed. |
| `INFERRED` | Explicitly marked as a reasoned inference and backed by existing file evidence. |
| `STALE` | Referenced commit SHA does not match the pinned snapshot SHA. |
| `UNAVAILABLE` | File missing, invalid line range, excerpt mismatch, or irrelevant claim text. |

**Anti-Hallucination Guarantee**: An LLM cannot self-certify its claims as verified. All claims must pass `EvidenceValidator.validate_claim()`.

---

### 6. Real GitHub Issue-to-Code Mapping

1. **Pull Request Exclusion**: Excludes PRs from beginner issue discovery.
2. **Symbol & Path Matching**:
   - Searches for explicit file paths mentioned in issue text.
   - Matches issue keywords against extracted AST symbols (function names, class names).
   - Falls back to filename matching only when no symbol match is found.
3. **Readiness Scoring Preservation**: Preserves the 7-criterion deterministic scoring model:
   - `issue_is_open` (25%)
   - `has_clear_description` (20%)
   - `not_stale` (15%)
   - `has_reproduction_or_steps` (15%)
   - `has_good_first_issue_label` (10%)
   - `language_match` (10%)
   - `has_tests_nearby` (5%)
4. **Honest Reporting**: When no reliable mapping can be established, `has_reliable_mapping = False`, `confidence = "none"`, and uncertainty notes are explicitly returned. No imaginary files are created.

---

### 7. Contribution Plan Generation & Plan Validation

Structured plans are generated across 6 stages:
1. **Understand**: Explains issue objective, references source evidence, lists ambiguities.
2. **Explore**: Details relevant functions, modules, and existing tests.
3. **Plan**: Small, ordered implementation steps linked to real source files.
4. **Attempt**: Guidance and patch templates. Explicit notice: FirstPatch AI does not auto-modify local user files.
5. **Verify**: Discovered test runners and static verification checklist.
6. **Prepare PR**: Structured PR summary, branch conventions, and testing evidence.

**Plan Validator (`PlanValidator`)**:
- Validates that every file referenced in the plan actually exists in the snapshot.
- Validates that commit SHAs match.
- Flags nonexistent files, invalid symbols, or stale evidence references.

---

### 8. Static Test Discovery Boundaries

- Inspects `pytest.ini`, `pyproject.toml`, `package.json`, test folders, and test files.
- Discovers test frameworks (pytest, Jest, Vitest, Mocha) and test function names.
- **Critical Security Boundary**:
  - Static inspection only.
  - Does NOT execute `pytest`, `npm test`, `pip install`, or any shell commands.
  - Flags `execution_performed = False` and `is_statically_discovered = True`.
  - Static discovery is never reported as a passing test run.

---

### 9. Phase 1 Integration Contract

Phase 1 can import the unified service from `app.services.repository_intelligence`:

```python
from app.services.repository_intelligence import (
    RepositoryIntelligenceService,
    get_repository_intelligence_service,
)

service = get_repository_intelligence_service()
```

#### Contract Methods
- `get_repository_snapshot(repository_url: str, commit_sha: Optional[str] = None) -> RepositorySnapshot`
- `analyze_code_structure(snapshot: RepositorySnapshot, target_files: Optional[list[str]] = None) -> CodeStructureReport`
- `validate_claim_evidence(snapshot: RepositorySnapshot, claim: ClaimRecord) -> EvidenceValidationResult`
- `build_evidence_bundle(snapshot: RepositorySnapshot, claims: list[ClaimRecord]) -> EvidenceBundle`
- `fetch_open_issues(owner: str, repo: str, state="open", per_page=30) -> list[GitHubIssue]`
- `find_relevant_source(snapshot: RepositorySnapshot, issue: GitHubIssue, code_report: Optional[CodeStructureReport] = None) -> SourceMappingResult`
- `rank_contribution_issues(request: IssueMatchRequest, snapshot: RepositorySnapshot, raw_issues: list[dict], code_report: Optional[CodeStructureReport] = None) -> IssueMatchResponse`
- `discover_test_configuration(snapshot: RepositorySnapshot, code_report: Optional[CodeStructureReport] = None) -> TestDiscoveryReport`
- `generate_contribution_plan(request: PlanRequest, snapshot: RepositorySnapshot, issue: GitHubIssue, code_report: Optional[CodeStructureReport] = None) -> StructuredContributionPlan`
- `validate_plan_evidence(plan: StructuredContributionPlan, snapshot: RepositorySnapshot, code_report: Optional[CodeStructureReport] = None) -> PlanValidationReport`

---

### 10. Security Checks & Safeguards

- **SSRF**: Strictly enforces `github.com` hostname via `normalize_github_url`.
- **Path Traversal**: `validate_repo_path` checks against `..`, null bytes, and absolute paths.
- **Secret Redaction**: `redact_sensitive_text` strips GitHub tokens, AWS keys, bearer tokens, private keys, and passwords.
- **Untrusted Content**: Repository text is never treated as system instructions.
- **Zero Command Execution**: Test discovery is strictly static.

---

### 11. Test Coverage Summary

- **Total Test Count**: 73 passing tests (40 Phase 0 baseline + 33 new Phase 2 tests).
- **Execution Command**: `.venv\Scripts\pytest.exe -v`
- **Result**: `73 passed in 2.07s`
- **Linter**: `ruff check app/services/repository_intelligence` returned 0 errors.
- **Type Checker**: `mypy` on `app/services/repository_intelligence` returned 0 errors.
