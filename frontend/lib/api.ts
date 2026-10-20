/**
 * Resolves API Base URL across environments:
 * - Runtime server functions (Next.js server-side): reads process.env.BACKEND_URL (Vercel service binding)
 * - Public environment configuration: reads process.env.NEXT_PUBLIC_API_URL
 * - Client-side in unified deployment (Vercel rewrites /api/*): uses relative path ""
 * - Local standalone development: defaults to "http://127.0.0.1:8000"
 */
export function getApiBaseUrl(): string {
  // 1. Next.js server-side runtime functions (reads Vercel service binding)
  if (typeof window === "undefined" && process.env.BACKEND_URL) {
    return process.env.BACKEND_URL.replace(/\/$/, "");
  }

  // 2. Explicit public API URL if configured
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }

  // 3. Client-side browser in unified deployment (Vercel rewrites /api/(.*) -> backend)
  if (typeof window !== "undefined") {
    return "";
  }

  // 4. Default fallback for local standalone execution
  return "http://127.0.0.1:8000";
}

export function apiUrl(path: string): string {
  const base = getApiBaseUrl();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

export async function fetchHealth() {
  try {
    const res = await fetch(apiUrl("/api/health"), { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchModelStatus() {
  try {
    const res = await fetch(apiUrl("/api/models/status"), { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function testModelInference() {
  const res = await fetch(apiUrl("/api/models/health-check"), { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "Inference health check failed");
  }
  return data;
}

export async function testCloudApiKey(apiKey: string, provider?: string, model?: string) {
  const res = await fetch(apiUrl("/api/models/test-cloud-key"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      api_key: apiKey,
      provider: provider || undefined,
      model: model || undefined
    })
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "Failed to verify cloud API key.");
  }
  return data;
}

export async function updateActiveModel(modelName: string) {
  const res = await fetch(apiUrl("/api/settings/models"), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_name: modelName })
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to update model");
  }
  return await res.json();
}

export async function analyzeRepository(
  url: string,
  options?: { apiKey?: string; provider?: string; model?: string }
) {
  let apiKey = options?.apiKey;
  let provider = options?.provider;
  let model = options?.model;

  if (typeof window !== "undefined") {
    if (!apiKey) {
      apiKey = localStorage.getItem("firstpatch_gemma_api_key") || localStorage.getItem("firstpatch_api_key") || undefined;
    }
    if (!provider) {
      provider = localStorage.getItem("firstpatch_provider") || (apiKey?.startsWith("AIza") ? "google_ai_studio" : undefined);
    }
    if (!model) {
      model = localStorage.getItem("firstpatch_model") || undefined;
    }
  }

  const res = await fetch(apiUrl("/api/repositories/analyze"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url,
      api_key: apiKey || undefined,
      provider: provider || undefined,
      model: model || undefined
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed." }));
    throw new Error(err.detail || "Failed to analyze repository.");
  }
  return await res.json();
}

export async function reanalyzeRepositoryWithGemma(
  owner: string,
  repo: string,
  options?: { apiKey?: string; provider?: string; model?: string }
) {
  let apiKey = options?.apiKey;
  let provider = options?.provider;
  let model = options?.model;

  if (typeof window !== "undefined") {
    if (!apiKey) {
      apiKey = localStorage.getItem("firstpatch_gemma_api_key") || localStorage.getItem("firstpatch_api_key") || undefined;
    }
    if (!provider) {
      provider = localStorage.getItem("firstpatch_provider") || (apiKey?.startsWith("AIza") ? "google_ai_studio" : undefined);
    }
    if (!model) {
      model = localStorage.getItem("firstpatch_model") || undefined;
    }
  }

  const res = await fetch(apiUrl(`/api/repositories/${owner}/${repo}/ai-analyze`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      api_key: apiKey || undefined,
      provider: provider || undefined,
      model: model || undefined
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Gemma 4 AI analysis failed." }));
    throw new Error(err.detail || "Failed to run Gemma 4 repository analysis.");
  }
  return await res.json();
}

export async function getRepoAiAnalysis(owner: string, repo: string) {
  const res = await fetch(apiUrl(`/api/repositories/${owner}/${repo}/ai-analysis`), { cache: "no-store" });
  if (!res.ok) {
    throw new Error("Failed to fetch repository AI analysis.");
  }
  return await res.json();
}

export async function listRepositories() {
  const res = await fetch(apiUrl("/api/repositories"), { cache: "no-store" });
  if (!res.ok) return [];
  return await res.json();
}

export async function getRepository(owner: string, repo: string) {
  const res = await fetch(apiUrl(`/api/repositories/${owner}/${repo}`), { cache: "no-store" });
  if (!res.ok) throw new Error("Repository not found in local index.");
  return await res.json();
}

export async function getRepositoryFiles(owner: string, repo: string) {
  const res = await fetch(apiUrl(`/api/repositories/${owner}/${repo}/files`), { cache: "no-store" });
  if (!res.ok) return [];
  return await res.json();
}

export async function getRepositoryFileContent(owner: string, repo: string, path: string) {
  const res = await fetch(apiUrl(`/api/repositories/${owner}/${repo}/file?path=${encodeURIComponent(path)}`), { cache: "no-store" });
  if (!res.ok) throw new Error("File not found.");
  return await res.json();
}

export async function getRepositoryArchitecture(owner: string, repo: string) {
  const res = await fetch(apiUrl(`/api/repositories/${owner}/${repo}/architecture`), { cache: "no-store" });
  if (!res.ok) return { modules: [], entrypoints: [], test_suite: [] };
  return await res.json();
}

export async function discoverIssues(repositoryId: string, skillLevel: string = "Beginner") {
  const res = await fetch(apiUrl("/api/issues/discover"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repository_id: repositoryId, skill_level: skillLevel })
  });
  if (!res.ok) return [];
  return await res.json();
}

export async function getIssueDetail(owner: string, repo: string, number: number) {
  const res = await fetch(apiUrl(`/api/issues/${owner}/${repo}/${number}`), { cache: "no-store" });
  if (!res.ok) throw new Error("Issue not found.");
  return await res.json();
}

export async function askMentor(params: {
  repositoryId: string;
  question: string;
  mode?: "learn" | "copilot";
  conversationId?: string;
  skillLevel?: string;
  apiKey?: string;
  provider?: string;
  model?: string;
}) {
  const res = await fetch(apiUrl("/api/mentor/ask"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      repository_id: params.repositoryId,
      question: params.question,
      mode: params.mode || "learn",
      conversation_id: params.conversationId,
      skill_level: params.skillLevel || "Beginner",
      api_key: params.apiKey || undefined,
      provider: params.provider || undefined,
      model: params.model || undefined
    })
  });
  if (!res.ok) throw new Error("Mentor query failed.");
  return await res.json();
}

export async function planContribution(params: {
  repositoryId: string;
  issueTitle: string;
  issueDescription: string;
  issueId?: string;
}) {
  const res = await fetch(apiUrl("/api/mentor/plan-contribution"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      repository_id: params.repositoryId,
      issue_title: params.issueTitle,
      issue_description: params.issueDescription,
      issue_id: params.issueId
    })
  });
  if (!res.ok) throw new Error("Failed to generate contribution plan.");
  return await res.json();
}

export async function createContribution(params: {
  repositoryId: string;
  title: string;
  description?: string;
  issueId?: string;
  steps?: any[];
}) {
  const res = await fetch(apiUrl("/api/contributions"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      repository_id: params.repositoryId,
      title: params.title,
      description: params.description || "",
      issue_id: params.issueId,
      steps: params.steps
    })
  });
  if (!res.ok) throw new Error("Failed to create contribution workspace.");
  return await res.json();
}

export async function listContributions() {
  const res = await fetch(apiUrl("/api/contributions"), { cache: "no-store" });
  if (!res.ok) return [];
  return await res.json();
}

export async function getContribution(id: string) {
  const res = await fetch(apiUrl(`/api/contributions/${id}`), { cache: "no-store" });
  if (!res.ok) throw new Error("Workspace not found.");
  return await res.json();
}

export async function updateStep(contributionId: string, stepId: string, status: string, notes?: string) {
  const res = await fetch(apiUrl(`/api/contributions/${contributionId}/steps/${stepId}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, user_notes: notes })
  });
  if (!res.ok) throw new Error("Failed to update step.");
  return await res.json();
}

export async function runVerification(command: string, workspaceId?: string, repositoryId?: string) {
  const res = await fetch(apiUrl("/api/verification/run"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command, workspace_id: workspaceId, repository_id: repositoryId })
  });
  if (!res.ok) throw new Error("Execution failed.");
  return await res.json();
}

export async function diagnoseSetupError(errorLog: string, language: string = "Python") {
  const res = await fetch(apiUrl("/api/verification/diagnose-error"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ error_log: errorLog, language })
  });
  if (!res.ok) throw new Error("Diagnosis failed.");
  return await res.json();
}

export async function analyzeDiff(diff: string, workspaceId?: string) {
  const res = await fetch(apiUrl("/api/review/analyze-diff"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ diff, workspace_id: workspaceId })
  });
  if (!res.ok) throw new Error("Review simulation failed.");
  return await res.json();
}

export async function getContributionReport(id: string) {
  const res = await fetch(apiUrl(`/api/contributions/${id}/report`), { cache: "no-store" });
  if (!res.ok) throw new Error("Report generation failed.");
  return await res.json();
}

export async function getLearningProfile() {
  const res = await fetch(apiUrl("/api/learning/profile"), { cache: "no-store" });
  if (!res.ok) return null;
  return await res.json();
}

export async function updateLearningProfile(profile: any) {
  const res = await fetch(apiUrl("/api/learning/profile"), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile)
  });
  return await res.json();
}

export async function resetDatabase() {
  const res = await fetch(apiUrl("/api/settings/reset-database"), { method: "POST" });
  return await res.json();
}

export async function getBeginnerGlossary() {
  const res = await fetch(apiUrl("/api/learning/glossary"), { cache: "no-store" });
  if (!res.ok) return { glossary: [] };
  return await res.json();
}

export async function getContributionSequence() {
  const res = await fetch(apiUrl("/api/learning/contribution-sequence"), { cache: "no-store" });
  if (!res.ok) return { sequence: [] };
  return await res.json();
}

export async function getRepositoryDocumentation(owner: string, repo: string) {
  const res = await fetch(apiUrl(`/api/repositories/${owner}/${repo}/documentation`), { cache: "no-store" });
  if (!res.ok) return null;
  return await res.json();
}

export async function generateRepositoryDocumentation(owner: string, repo: string) {
  const res = await fetch(apiUrl(`/api/repositories/${owner}/${repo}/generate-docs`), { method: "POST" });
  if (!res.ok) throw new Error("Documentation generation failed.");
  return await res.json();
}

export async function runModelBenchmark(model?: string) {
  const path = model ? `/api/benchmark/model-run?model=${encodeURIComponent(model)}` : `/api/benchmark/model-run`;
  const res = await fetch(apiUrl(path), { method: "POST" });
  if (!res.ok) throw new Error("Benchmark run failed.");
  return await res.json();
}

export async function getIssueInvestigation(owner: string, repo: string, number: number) {
  const res = await fetch(apiUrl(`/api/issues/${owner}/${repo}/${number}/investigation`), { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load issue investigation.");
  return await res.json();
}

export async function getIssueTriage(owner: string, repo: string, number: number) {
  const res = await fetch(apiUrl(`/api/issues/${owner}/${repo}/${number}/triage`), { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load issue triage.");
  return await res.json();
}

export async function saveIssueTriage(owner: string, repo: string, number: number, triageData: any) {
  const res = await fetch(apiUrl(`/api/issues/${owner}/${repo}/${number}/triage`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(triageData)
  });
  if (!res.ok) throw new Error("Failed to save triage notes.");
  return await res.json();
}

export async function addIssueHypothesis(owner: string, repo: string, number: number, data: any) {
  const res = await fetch(apiUrl(`/api/issues/${owner}/${repo}/${number}/hypotheses`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error("Failed to add hypothesis.");
  return await res.json();
}

export async function updateIssueHypothesisStatus(owner: string, repo: string, number: number, hypoId: string, status: string, uncertainty?: string) {
  const res = await fetch(apiUrl(`/api/issues/${owner}/${repo}/${number}/hypotheses/${hypoId}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, remaining_uncertainty: uncertainty })
  });
  if (!res.ok) throw new Error("Failed to update hypothesis.");
  return await res.json();
}

export async function getMaintainerDrafts(owner: string, repo: string, number: number) {
  const res = await fetch(apiUrl(`/api/issues/${owner}/${repo}/${number}/maintainer-drafts`), { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load maintainer communication drafts.");
  return await res.json();
}

export async function getComplianceReport() {
  const res = await fetch(apiUrl("/api/compliance/report"), { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load compliance report.");
  return await res.json();
}

export async function bookmarkRepository(owner: string, repo: string) {
  if (typeof window !== "undefined") {
    try {
      const stored = localStorage.getItem("firstpatch_bookmarks");
      const bookmarks: string[] = stored ? JSON.parse(stored) : [];
      const key = `${owner}/${repo}`;
      if (!bookmarks.includes(key)) {
        bookmarks.push(key);
        localStorage.setItem("firstpatch_bookmarks", JSON.stringify(bookmarks));
      }
      return { status: "success", bookmarked: true };
    } catch {
      return { status: "success", bookmarked: true };
    }
  }
  return { status: "success", bookmarked: true };
}
