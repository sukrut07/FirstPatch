# FirstPatch AI — Implementation Plan

## Phase 0: Foundation (Current — Completed)

### Completed Work

| Component | Status | Notes |
|---|---|---|
| Project monorepo structure | ✅ Done | `frontend/` + `backend/` + `docs/` |
| Backend FastAPI app | ✅ Done | With lifespan, CORS, routing |
| Pydantic v2 schemas | ✅ Done | Full API contract defined |
| SQLAlchemy 2.x SQLite persistence | ✅ Done | repository_cache, sessions, issue_cache |
| GitHub service (URL norm, metadata, issues, tree, README) | ✅ Done | SSRF protection, rate limit handling |
| Repository analysis service | ✅ Done | Framework/config/test detection |
| Issue matching engine (7-criterion deterministic) | ✅ Done | Transparent scoring |
| Mentor/contribution plan service | ✅ Done | Evidence-backed steps |
| Setup diagnostics service | ✅ Done | Pattern-based, no command execution |
| AI provider adapter (Google AI Studio + Ollama + fallback) | ✅ Done | Deterministic fallback active |
| Health endpoint | ✅ Done | No credential exposure |
| All API routes | ✅ Done | 9 endpoints |
| Next.js 14 frontend | ✅ Done | App Router + TypeScript strict |
| Tailwind CSS design system | ✅ Done | Dark-first, developer aesthetic |
| Home / analyze view | ✅ Done | URL validation, demo repos |
| Repository overview view | ✅ Done | Evidence refs, frameworks, languages |
| Issue explorer view | ✅ Done | Search, filter, criterion expansion |
| Contribution plan view | ✅ Done | Steps, prerequisites, uncertainties |
| Settings / health view | ✅ Done | Service status, AI config guidance |
| Backend test suite | ✅ Done | 40 unit and integration tests (100% passing) |
| Frontend compilation & lint | ✅ Done | TypeScript 0 errors, ESLint 0 errors, Next.js build clean |
| Browser verification | ✅ Done | Full interactive flow verified via automated browser agent |
| Documentation (README, ARCH, API, SECURITY, PLAN) | ✅ Done | Comprehensive documentation set |
| .gitignore, .env.example | ✅ Done | |

### First Vertical Slice

The following end-to-end flow works in Phase 0:

```
Public GitHub URL
  → URL normalization + SSRF validation
  → Real GitHub API: metadata, SHA, languages, tree, README
  → Evidence-backed RepositoryOverview
  → Real GitHub API: open issues (paginated, PRs excluded)
  → Deterministic 7-criterion issue ranking
  → Evidence-backed ContributionPlan with explicit steps
  → Honest uncertainties and assumptions listed
```

---

## Phase 1: Enhancement (Next)

### High Priority

1. **AST-based file analysis** (Python)
   - Parse `import` statements from fetched files
   - Identify functions and classes relevant to issue keywords
   - Generate `AST_FUNCTION` and `AST_IMPORT` evidence references
   - Dependency: Requires fetching individual files (within rate limits)

2. **Database caching with TTL**
   - Wire `RepositoryCache` and `IssueCache` ORM models to analysis services
   - Return cached results with `cache_expires_at` header
   - Detect stale analysis when `commit_sha` changes

3. **Contributor profile persistence**
   - Store skills, experience level, and preferences in `ContributionSession`
   - Pre-fill issue matching with stored preferences

4. **AI enrichment for issue matching**
   - When Gemma is available, generate natural-language summaries of why an issue matches
   - Label AI content clearly; keep deterministic scores unchanged

5. **GitHub authenticated session**
   - Optional token management UI (token stored server-side, never in browser)
   - Show rate limit status in Settings

### Medium Priority

6. **Sandboxed test execution**
   - Docker-based execution with resource limits
   - Show actual test output in Verification view
   - Mark failed tests with evidence references

7. **PR preparation checklist**
   - Interactive checklist in Plan view
   - Git diff preview support

8. **Multi-language AST support**
   - TypeScript / JavaScript import analysis
   - Go package analysis

### Low Priority

9. **Maintainer view**
   - Generate "first-contribution guide" for an issue
   - Exportable as GitHub issue comment template

10. **Repository freshness tracking**
    - Periodic re-analysis when commit SHA changes
    - Notify user of stale analysis

---

## Known Limitations

| Limitation | Impact | Phase |
|---|---|---|
| No test execution | Cannot verify fixes | Phase 1 |
| No AST analysis | File matching is keyword-based only | Phase 1 |
| No response caching | Analysis re-runs on every request | Phase 1 |
| No authenticated GitHub session UI | PAT must be set in .env | Phase 1 |
| AI enrichment not yet wired to plans | Plans are deterministic only | Phase 1 |
| No pull-request preparation workflow | PR checklist is manual | Phase 2 |
| No vector search for large repos | Keyword matching only | Phase 2 |

---

## Task Dependencies

```
Phase 0 (Complete)
  └── Phase 1A: AST analysis → richer relevant_files
  └── Phase 1B: DB caching → performance + staleness detection
       └── Phase 1C: AI enrichment (needs repo data from cache)
  └── Phase 1D: Test execution sandbox → Phase 2: PR workflow
```

---

## Next Recommended Task

**Implement Python AST analysis for file-level intelligence.**

1. Fetch top-N files most likely relevant to the issue (by keyword match score)
2. Parse with `ast` module (already available in standard library)
3. Extract: imports, function names, class names, docstrings
4. Match against issue keywords
5. Create `AST_FUNCTION` evidence references with line numbers
6. Return in `ContributionPlan.relevant_files` with real line ranges

This would be the most impactful single improvement to plan quality and is entirely deterministic.
