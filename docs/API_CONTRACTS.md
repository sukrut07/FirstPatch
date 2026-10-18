# FirstPatch AI — API Contracts

Base URL: `http://localhost:8000` (development)

All endpoints return JSON. Errors follow the format:
```json
{ "detail": "Human-readable error message" }
```

---

## Health

### `GET /api/health`

Returns service status without exposing credentials.

**Response 200:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "ai_provider": "deterministic_fallback",
  "ai_provider_status": "not_configured",
  "github_authenticated": false,
  "timestamp": "2024-10-18T07:00:00Z"
}
```

`ai_provider_status` values: `available | unavailable | degraded | not_configured`

---

## Repository Analysis

### `POST /api/repositories/analyze`

Analyzes a public GitHub repository.

**Request:**
```json
{ "url": "https://github.com/tiangolo/fastapi" }
```

**Response 200:**
```json
{
  "session_id": "uuid",
  "analysis_duration_ms": 1423,
  "repository": {
    "identity": { "owner": "tiangolo", "repo": "fastapi" },
    "full_name": "tiangolo/fastapi",
    "description": "FastAPI framework, high performance...",
    "primary_language": "Python",
    "default_branch": "master",
    "commit_sha": "abc123...",
    "stars": 75000,
    "forks": 6400,
    "open_issues_count": 280,
    "archived": false,
    "github_url": "https://github.com/tiangolo/fastapi",
    "readme_summary": "FastAPI is a modern, fast...",
    "detected_frameworks": [
      { "name": "FastAPI", "confidence": "likely", "evidence": [...] },
      { "name": "Pytest",  "confidence": "likely", "evidence": [...] }
    ],
    "config_files": ["pyproject.toml", "requirements.txt"],
    "test_locations": [
      { "path": "tests", "framework": "pytest (likely)" }
    ],
    "directory_snapshot": ["docs", "fastapi", "tests", "scripts"],
    "detected_languages": { "Python": 98.5, "Shell": 1.5 },
    "analysis_status": "complete",
    "analysis_warnings": [],
    "evidence_refs": [
      {
        "id": "uuid",
        "owner": "tiangolo",
        "repo": "fastapi",
        "commit_sha": "abc123",
        "evidence_type": "repository_metadata",
        "status": "verified",
        "retrieved_at": "2024-10-18T07:00:00Z"
      }
    ],
    "analyzed_at": "2024-10-18T07:00:00Z"
  }
}
```

**Errors:**
- `422` — Invalid or non-GitHub URL
- `404` — Repository not found or private
- `429` — GitHub rate limit exceeded
- `502` — GitHub API error

---

### `GET /api/repositories/{owner}/{repo}`

Returns fresh repository analysis for an owner/repo pair.

**Response:** Same as `POST /api/repositories/analyze` `.repository` field.

---

## Issues

### `GET /api/repositories/{owner}/{repo}/issues`

Lists open issues, excluding pull requests.

**Query parameters:**
- `page` (int, default 1, max 100)
- `per_page` (int, default 30, max 100)
- `state` (string: `open | closed | all`, default `open`)
- `labels` (string, comma-separated label names)

**Response 200:** Array of `GitHubIssue` objects:
```json
[
  {
    "number": 42,
    "title": "Fix login error with special characters",
    "state": "open",
    "body": "...",
    "labels": [
      { "name": "good first issue", "color": "7057ff" }
    ],
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-06-10T12:00:00Z",
    "author": "testuser",
    "comment_count": 3,
    "github_url": "https://github.com/owner/repo/issues/42",
    "is_pull_request": false
  }
]
```

---

### `POST /api/issues/match`

Matches issues to a contributor profile with transparent scoring.

**Request:**
```json
{
  "owner": "tiangolo",
  "repo": "fastapi",
  "skills": ["python", "http"],
  "preferred_languages": ["python"],
  "experience_level": "beginner",
  "available_hours": 4,
  "learning_preferences": []
}
```

**Response 200:**
```json
{
  "owner": "tiangolo",
  "repo": "fastapi",
  "matched_issues": [
    {
      "issue": { ... },
      "total_score": 0.73,
      "difficulty": "beginner",
      "difficulty_explanation": "Estimated beginner-friendly based on: maintainer-applied 'good first issue' label, contains reproduction steps. This is a heuristic — verify by reading the full issue.",
      "criteria": [
        {
          "name": "issue_is_open",
          "passed": true,
          "score": 1.0,
          "explanation": "The issue is currently open and has not been closed.",
          "missing_data": false
        },
        {
          "name": "has_clear_description",
          "passed": true,
          "score": 0.9,
          "explanation": "Issue has a description (847 chars).",
          "missing_data": false
        }
      ],
      "prerequisites": ["Python fundamentals", "FastAPI basics", "Git: fork → branch → commit → push → PR workflow"],
      "risks": [
        "No contribution is guaranteed to be accepted. Read CONTRIBUTING.md..."
      ],
      "ai_enrichment": null,
      "ai_enrichment_available": false
    }
  ],
  "total_issues_considered": 30,
  "scoring_explanation": "Issues are ranked by a weighted heuristic score across 7 criteria...",
  "warnings": []
}
```

**Scoring criteria and weights:**
| Criterion | Weight | Description |
|---|---|---|
| `issue_is_open` | 25% | Issue is currently open |
| `has_clear_description` | 20% | Description is informative |
| `not_stale` | 15% | Updated within 180 days |
| `has_reproduction_or_steps` | 15% | Contains reproduction steps |
| `has_good_first_issue_label` | 10% | Has beginner label (hint, not guarantee) |
| `language_match` | 10% | Skills align with repository languages |
| `has_tests_nearby` | 5% | Test directories detected |

---

## Mentor

### `POST /api/mentor/plan`

Generates a contribution plan for a specific issue.

**Request:**
```json
{
  "owner": "tiangolo",
  "repo": "fastapi",
  "issue_number": 42,
  "contributor_skills": ["python"],
  "experience_level": "beginner"
}
```

**Response 200:**
```json
{
  "session_id": "uuid",
  "owner": "tiangolo",
  "repo": "fastapi",
  "issue_number": 42,
  "issue_title": "Fix login error...",
  "issue_url": "https://github.com/tiangolo/fastapi/issues/42",
  "summary": "This plan guides you through contributing a fix...",
  "relevant_files": ["fastapi", "tests"],
  "implementation_steps": [
    {
      "order": 1,
      "description": "Read the full issue and all comments carefully",
      "rationale": "Understanding the exact problem...",
      "relevant_files": [],
      "is_verified": false
    }
  ],
  "suggested_tests": ["Run existing tests in 'tests' using pytest (likely)..."],
  "prerequisite_concepts": ["Python fundamentals", "FastAPI basics"],
  "evidence_refs": [...],
  "uncertainties": [],
  "assumptions": ["This plan is based on publicly available repository metadata..."],
  "ai_generated": false,
  "generated_at": "2024-10-18T07:00:00Z"
}
```

---

### `POST /api/mentor/diagnose`

Diagnoses a setup error. Does NOT execute commands.

**Request:**
```json
{
  "owner": "tiangolo",
  "repo": "fastapi",
  "error_description": "ModuleNotFoundError: No module named 'fastapi'",
  "command_output": "Traceback (most recent call last)...",
  "config_snippets": []
}
```

**Response 200:**
```json
{
  "owner": "tiangolo",
  "repo": "fastapi",
  "findings": [
    {
      "likely_cause": "A required dependency is not installed",
      "supporting_evidence": ["Error output contains module-not-found indicators"],
      "safe_diagnostic_steps": ["Run: pip install -r requirements.txt"],
      "suggested_fix": "Install dependencies as documented in the README",
      "verification_steps": ["Run the failed command again after installing"],
      "confidence": "high",
      "is_verified": false
    }
  ],
  "disclaimer": "These suggestions are based on repository analysis and common patterns. They have not been executed or verified...",
  "ai_generated": false
}
```

**Validation:** `error_description` max 2000 chars; `command_output` max 5000 chars.

---

## Verification

### `GET /api/verification/{session_id}`

Returns verification status for a contribution session.

**Response 200:**
```json
{
  "session_id": "uuid",
  "owner": "unknown",
  "repo": "unknown",
  "checks": [
    {
      "name": "test_suite",
      "description": "Run the project's test suite to verify the fix",
      "status": "unavailable",
      "result_detail": "Test execution requires an isolated environment and is not available in Phase 0."
    },
    {
      "name": "contribution_checklist",
      "description": "Basic contribution readiness checklist",
      "status": "not_run",
      "result_detail": "Items to check manually: ..."
    }
  ],
  "overall_ready": false,
  "blockers": ["Test execution is not available in Phase 0..."],
  "updated_at": "2024-10-18T07:00:00Z"
}
```

Check status values: `passed | failed | skipped | not_run | unavailable`
