# FirstPatch AI — Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                      Browser (User)                      │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON
┌──────────────────────▼──────────────────────────────────┐
│              Next.js Frontend (port 3000)                │
│  Pages: Home | Overview | Issues | Plan | Settings      │
│  lib/api.ts — type-safe API client                      │
│  components/ui.tsx — shared design system               │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON (localhost:8000)
┌──────────────────────▼──────────────────────────────────┐
│               FastAPI Backend (port 8000)                │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                  API Routes                       │   │
│  │  /api/health  /api/repositories  /api/issues    │   │
│  │  /api/mentor  /api/verification                  │   │
│  └──────────┬──────────────────┬────────────────────┘   │
│             │                  │                         │
│  ┌──────────▼──────┐  ┌────────▼────────────────────┐  │
│  │  GitHub Service │  │     Domain Services          │  │
│  │  - URL normalize│  │  - RepositoryAnalysis        │  │
│  │  - Metadata     │  │  - IssueMatchingEngine       │  │
│  │  - Issues       │  │  - MentorService/Planner     │  │
│  │  - File content │  │  - DiagnosticService         │  │
│  │  - Rate limits  │  │  - VerificationService       │  │
│  └──────────┬──────┘  └────────┬────────────────────┘  │
│             │                  │                         │
│             ▼                  ▼                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │         AI Provider Adapter                        │ │
│  │  GoogleAIStudioProvider (Gemma) | OllamaProvider  │ │
│  │  DeterministicFallbackProvider (always available) │ │
│  └────────────────────────────────────────────────────┘ │
│                         │                               │
│  ┌──────────────────────▼─────────────────────────────┐ │
│  │         SQLite (SQLAlchemy 2.x async)              │ │
│  │  repository_cache | contribution_sessions          │ │
│  │  issue_cache                                       │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                       │ HTTPS
         ┌─────────────▼──────────────┐
         │     GitHub REST API        │
         │  api.github.com            │
         └────────────────────────────┘
```

## Data Flow: Repository Analysis

```
1. User enters GitHub URL
   ↓
2. Frontend validates format (client-side)
   ↓
3. POST /api/repositories/analyze
   ↓
4. Backend normalizes + validates URL (SSRF protection)
   ↓
5. GitHubService.get_repository_metadata()  → EvidenceRef(REPOSITORY_METADATA)
   ↓
6. GitHubService.get_default_branch_sha()   → commit_sha (pins analysis)
   ↓
7. GitHubService.get_languages()            → detected_languages
   ↓
8. GitHubService.get_tree()                 → directory structure
   ↓
9. Detect config files, test directories, frameworks from tree
   ↓
10. GitHubService.get_readme()              → EvidenceRef(README_STATEMENT)
    ↓
11. Assemble RepositoryOverview with all EvidenceRefs
    ↓
12. Return AnalyzeRepositoryResponse
```

## Evidence Model

The `EvidenceRef` type is the foundation of honesty in this system. Every displayed fact must be traceable to an `EvidenceRef`:

```python
class EvidenceRef:
    id: UUID                  # Unique identifier
    owner: str                # Repository owner
    repo: str                 # Repository name
    commit_sha: Optional[str] # Pins to specific snapshot
    file_path: Optional[str]  # Source file
    github_url: Optional[str] # Clickable GitHub link
    start_line: Optional[int] # Source line range
    end_line: Optional[int]
    evidence_type: EvidenceType
    excerpt: Optional[str]    # Safe, bounded content excerpt
    retrieved_at: datetime    # When this was fetched
    status: EvidenceStatus    # verified | inferred | unavailable | stale
    confidence_note: Optional[str]  # Uncertainty disclosure
```

Evidence types:
- `REPOSITORY_METADATA` — from GitHub API `/repos/{owner}/{repo}`
- `README_STATEMENT` — from decoded README content
- `CONFIG_DECLARATION` — from identified configuration file
- `AST_FUNCTION` / `AST_IMPORT` — from Python AST analysis (Phase 1)
- `EXISTING_TEST` — from test directory detection
- `GITHUB_ISSUE_FIELD` — from GitHub Issues API
- `DIRECTORY_STRUCTURE` — from git tree analysis
- `INFERRED` — model-generated, not source-derived

## AI Orchestration

The AI provider is an optional enrichment layer, not a requirement:

```
Request
  ↓
Deterministic analysis (always runs)
  ↓
[If AI provider available]
  ↓
AI enrichment with structured output validation
  ↓
Merge: deterministic facts + AI explanations (clearly labelled)
```

The AI model receives only the relevant repository evidence, never:
- Full source code dumps
- User credentials
- System instructions embedded in repository content

Repository content is always framed as untrusted data in the model prompt.

## Storage Design

Phase 0 uses SQLite via SQLAlchemy 2.x async:

- `repository_cache`: Cached analysis with TTL (default: 1 hour)
- `contribution_sessions`: Per-session contribution journey (Flight Recorder foundation)
- `issue_cache`: Cached issue lists with TTL

The schema is designed to be migrated to PostgreSQL without application changes.

## Security Boundaries

```
[Internet]
    │
    │ HTTPS only, github.com allowlist
    ▼
[GitHub API Client]     ← bounded timeouts, size limits, rate limit handling
    │
    │ Untrusted data
    ▼
[Repository Analysis]   ← content treated as data, not instructions
    │
    │ Structured evidence only
    ▼
[AI Provider]           ← receives evidence, not raw content
                        ← cannot execute code or access secrets
    │
    │ Validated Pydantic output
    ▼
[API Response]          ← no credentials, no file system paths leaked
    │
    │ JSON
    ▼
[Frontend]              ← all external links open in new tab with noopener
```
