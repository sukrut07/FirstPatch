/**
 * FirstPatch AI — API Client
 * Type-safe client for the backend API.
 * All types mirror the backend Pydantic schemas.
 */

// ---------------------------------------------------------------------------
// Type Definitions (mirroring backend schemas)
// ---------------------------------------------------------------------------

export type AnalysisStatus = 'pending' | 'in_progress' | 'complete' | 'failed' | 'partial';
export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced' | 'unknown';
export type EvidenceType =
  | 'repository_metadata'
  | 'readme_statement'
  | 'config_declaration'
  | 'ast_function'
  | 'ast_import'
  | 'existing_test'
  | 'github_issue_field'
  | 'directory_structure'
  | 'executed_command'
  | 'inferred';
export type EvidenceStatus = 'verified' | 'inferred' | 'unavailable' | 'stale';
export type AIProviderStatus = 'available' | 'unavailable' | 'degraded' | 'not_configured';
export type CheckStatus = 'passed' | 'failed' | 'skipped' | 'not_run' | 'unavailable';

export interface EvidenceRef {
  id: string;
  owner: string;
  repo: string;
  commit_sha?: string;
  file_path?: string;
  github_url?: string;
  start_line?: number;
  end_line?: number;
  evidence_type: EvidenceType;
  excerpt?: string;
  retrieved_at: string;
  status: EvidenceStatus;
  confidence_note?: string;
}

export interface RepositoryIdentity {
  owner: string;
  repo: string;
}

export interface DetectedFramework {
  name: string;
  confidence: 'certain' | 'likely' | 'possible';
  evidence: EvidenceRef[];
}

export interface TestLocation {
  path: string;
  framework?: string;
  evidence?: EvidenceRef;
}

export interface RepositoryOverview {
  identity: RepositoryIdentity;
  full_name: string;
  description?: string;
  primary_language?: string;
  topics: string[];
  default_branch: string;
  commit_sha?: string;
  stars: number;
  forks: number;
  open_issues_count: number;
  archived: boolean;
  license_name?: string;
  github_url: string;
  created_at?: string;
  updated_at?: string;
  readme_summary?: string;
  detected_frameworks: DetectedFramework[];
  config_files: string[];
  test_locations: TestLocation[];
  directory_snapshot: string[];
  detected_languages: Record<string, number>;
  analysis_status: AnalysisStatus;
  analysis_warnings: string[];
  evidence_refs: EvidenceRef[];
  analyzed_at?: string;
  cache_expires_at?: string;
}

export interface AnalyzeRepositoryResponse {
  repository: RepositoryOverview;
  session_id: string;
  analysis_duration_ms?: number;
}

export interface IssueLabel {
  name: string;
  color?: string;
  description?: string;
}

export interface GitHubIssue {
  number: number;
  title: string;
  state: string;
  body?: string;
  labels: IssueLabel[];
  created_at: string;
  updated_at: string;
  closed_at?: string;
  author?: string;
  comment_count: number;
  github_url: string;
  is_pull_request: boolean;
}

export interface IssueMatchCriterion {
  name: string;
  passed: boolean;
  score: number;
  explanation: string;
  evidence?: EvidenceRef;
  missing_data: boolean;
}

export interface MatchedIssue {
  issue: GitHubIssue;
  total_score: number;
  difficulty: DifficultyLevel;
  difficulty_explanation: string;
  criteria: IssueMatchCriterion[];
  prerequisites: string[];
  relevant_files: string[];
  risks: string[];
  ai_enrichment?: string;
  ai_enrichment_available: boolean;
}

export interface IssueMatchResponse {
  owner: string;
  repo: string;
  matched_issues: MatchedIssue[];
  total_issues_considered: number;
  scoring_explanation: string;
  warnings: string[];
}

export interface ImplementationStep {
  order: number;
  description: string;
  rationale: string;
  relevant_files: string[];
  evidence?: EvidenceRef;
  is_verified: boolean;
}

export interface ContributionPlan {
  session_id: string;
  owner: string;
  repo: string;
  issue_number: number;
  issue_title: string;
  issue_url: string;
  summary: string;
  relevant_files: string[];
  implementation_steps: ImplementationStep[];
  suggested_tests: string[];
  prerequisite_concepts: string[];
  evidence_refs: EvidenceRef[];
  uncertainties: string[];
  assumptions: string[];
  ai_generated: boolean;
  generated_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  ai_provider: string;
  ai_provider_status: AIProviderStatus;
  github_authenticated: boolean;
  timestamp: string;
}

export interface IssueMatchRequest {
  owner: string;
  repo: string;
  skills: string[];
  preferred_languages: string[];
  experience_level: DifficultyLevel;
  available_hours?: number;
  learning_preferences: string[];
}

export interface DiagnosticRequest {
  owner: string;
  repo: string;
  error_description: string;
  command_output?: string;
  config_snippets?: string[];
}

// ---------------------------------------------------------------------------
// API Client
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    throw new APIError(
      `API request failed: ${response.status} ${response.statusText}`,
      response.status,
      detail
    );
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API Methods
// ---------------------------------------------------------------------------

export const api = {
  health: (): Promise<HealthResponse> =>
    apiFetch('/api/health'),

  analyzeRepository: (url: string): Promise<AnalyzeRepositoryResponse> =>
    apiFetch('/api/repositories/analyze', {
      method: 'POST',
      body: JSON.stringify({ url }),
    }),

  getRepository: (owner: string, repo: string): Promise<RepositoryOverview> =>
    apiFetch(`/api/repositories/${owner}/${repo}`),

  listIssues: (
    owner: string,
    repo: string,
    params?: { page?: number; per_page?: number; state?: string; labels?: string }
  ): Promise<GitHubIssue[]> => {
    const query = new URLSearchParams();
    if (params?.page) query.set('page', String(params.page));
    if (params?.per_page) query.set('per_page', String(params.per_page));
    if (params?.state) query.set('state', params.state);
    if (params?.labels) query.set('labels', params.labels);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiFetch(`/api/repositories/${owner}/${repo}/issues${qs}`);
  },

  matchIssues: (request: IssueMatchRequest): Promise<IssueMatchResponse> =>
    apiFetch('/api/issues/match', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  generatePlan: (
    owner: string,
    repo: string,
    issueNumber: number,
    skills?: string[],
    experienceLevel?: DifficultyLevel
  ): Promise<ContributionPlan> =>
    apiFetch('/api/mentor/plan', {
      method: 'POST',
      body: JSON.stringify({
        owner,
        repo,
        issue_number: issueNumber,
        contributor_skills: skills ?? [],
        experience_level: experienceLevel ?? 'beginner',
      }),
    }),

  diagnoseSetup: (request: DiagnosticRequest) =>
    apiFetch('/api/mentor/diagnose', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  getVerification: (sessionId: string): Promise<VerificationStatus> =>
    apiFetch(`/api/verification/${sessionId}`),

  getVerificationHealth: (): Promise<VerificationInfrastructureHealth> =>
    apiFetch('/api/verification/health'),

  submitVerificationRun: (req: VerificationRunRequest): Promise<VerificationRunRecord> =>
    apiFetch('/api/verification/run', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  getVerificationRun: (runId: string): Promise<VerificationRunRecord> =>
    apiFetch(`/api/verification/runs/${runId}`),

  cancelVerificationRun: (runId: string): Promise<{ cancelled: boolean }> =>
    apiFetch(`/api/verification/runs/${runId}/cancel`, {
      method: 'POST',
    }),
};

// ---------------------------------------------------------------------------
// Phase 3 Verification Types
// ---------------------------------------------------------------------------

export type ExecutionStatus =
  | 'queued'
  | 'preparing'
  | 'running'
  | 'passed'
  | 'failed'
  | 'timed_out'
  | 'blocked'
  | 'unsupported'
  | 'unavailable'
  | 'cancelled';

export type RuntimeProfile = 'python_pytest' | 'node_jest' | 'node_npm_test';

export interface VerificationRunRequest {
  owner: string;
  repo: string;
  commit_sha: string;
  runtime?: RuntimeProfile;
  test_target?: string;
  timeout_seconds?: number;
  session_id?: string;
}

export interface VerificationTestCounts {
  collected: number;
  passed: number;
  failed: number;
  skipped: number;
  errors: number;
}

export interface VerificationRunRecord {
  run_id: string;
  session_id?: string;
  owner: string;
  repo: string;
  commit_sha: string;
  runtime: RuntimeProfile;
  test_target: string;
  status: ExecutionStatus;
  exit_code?: number;
  counts?: VerificationTestCounts;
  stdout: string;
  stderr: string;
  error_summary?: string;
  started_at: string;
  finished_at?: string;
  duration_ms?: number;
  cleanup_performed: boolean;
  cleanup_error?: string;
  warnings: string[];
}

export interface VerificationInfrastructureHealth {
  runtime_available: boolean;
  runtime_name: string;
  isolation_level: string;
  supported_profiles: RuntimeProfile[];
  message: string;
  host_execution_permitted: boolean;
}

export interface VerificationCheck {
  name: string;
  description: string;
  status: CheckStatus;
  result_detail?: string;
  ran_at?: string;
  evidence?: EvidenceRef;
}

export interface VerificationStatus {
  session_id: string;
  owner: string;
  repo: string;
  checks: VerificationCheck[];
  overall_ready: boolean;
  blockers: string[];
  updated_at: string;
}

