const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchModelStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/models/status`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function analyzeRepository(url: string) {
  const res = await fetch(`${API_BASE}/api/repositories/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed." }));
    throw new Error(err.detail || "Failed to analyze repository.");
  }
  return await res.json();
}

export async function listRepositories() {
  const res = await fetch(`${API_BASE}/api/repositories`, { cache: "no-store" });
  if (!res.ok) return [];
  return await res.json();
}

export async function getRepository(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repositories/${owner}/${repo}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Repository not found in local index.");
  return await res.json();
}

export async function getRepositoryFiles(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repositories/${owner}/${repo}/files`, { cache: "no-store" });
  if (!res.ok) return [];
  return await res.json();
}

export async function getRepositoryFileContent(owner: string, repo: string, path: string) {
  const res = await fetch(`${API_BASE}/api/repositories/${owner}/${repo}/file?path=${encodeURIComponent(path)}`, { cache: "no-store" });
  if (!res.ok) throw new Error("File not found.");
  return await res.json();
}

export async function getRepositoryArchitecture(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repositories/${owner}/${repo}/architecture`, { cache: "no-store" });
  if (!res.ok) return { modules: [], entrypoints: [], test_suite: [] };
  return await res.json();
}

export async function discoverIssues(repositoryId: string, skillLevel: string = "Beginner") {
  const res = await fetch(`${API_BASE}/api/issues/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repository_id: repositoryId, skill_level: skillLevel })
  });
  if (!res.ok) return [];
  return await res.json();
}

export async function getIssueDetail(owner: string, repo: string, number: number) {
  const res = await fetch(`${API_BASE}/api/issues/${owner}/${repo}/${number}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Issue not found.");
  return await res.json();
}

export async function askMentor(params: {
  repositoryId: string;
  question: string;
  mode?: "learn" | "copilot";
  conversationId?: string;
  skillLevel?: string;
}) {
  const res = await fetch(`${API_BASE}/api/mentor/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      repository_id: params.repositoryId,
      question: params.question,
      mode: params.mode || "learn",
      conversation_id: params.conversationId,
      skill_level: params.skillLevel || "Beginner"
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
  const res = await fetch(`${API_BASE}/api/mentor/plan-contribution`, {
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
  const res = await fetch(`${API_BASE}/api/contributions`, {
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
  const res = await fetch(`${API_BASE}/api/contributions`, { cache: "no-store" });
  if (!res.ok) return [];
  return await res.json();
}

export async function getContribution(id: string) {
  const res = await fetch(`${API_BASE}/api/contributions/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Workspace not found.");
  return await res.json();
}

export async function updateStep(contributionId: string, stepId: string, status: string, notes?: string) {
  const res = await fetch(`${API_BASE}/api/contributions/${contributionId}/steps/${stepId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, user_notes: notes })
  });
  if (!res.ok) throw new Error("Failed to update step.");
  return await res.json();
}

export async function runVerification(command: string, workspaceId?: string, repositoryId?: string) {
  const res = await fetch(`${API_BASE}/api/verification/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command, workspace_id: workspaceId, repository_id: repositoryId })
  });
  if (!res.ok) throw new Error("Execution failed.");
  return await res.json();
}

export async function diagnoseSetupError(errorLog: string, language: string = "Python") {
  const res = await fetch(`${API_BASE}/api/verification/diagnose-error`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ error_log: errorLog, language })
  });
  if (!res.ok) throw new Error("Diagnosis failed.");
  return await res.json();
}

export async function analyzeDiff(diff: string, workspaceId?: string) {
  const res = await fetch(`${API_BASE}/api/review/analyze-diff`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ diff, workspace_id: workspaceId })
  });
  if (!res.ok) throw new Error("Review simulation failed.");
  return await res.json();
}

export async function getContributionReport(id: string) {
  const res = await fetch(`${API_BASE}/api/contributions/${id}/report`, { cache: "no-store" });
  if (!res.ok) throw new Error("Report generation failed.");
  return await res.json();
}

export async function getLearningProfile() {
  const res = await fetch(`${API_BASE}/api/learning/profile`, { cache: "no-store" });
  if (!res.ok) return null;
  return await res.json();
}

export async function updateLearningProfile(profile: any) {
  const res = await fetch(`${API_BASE}/api/learning/profile`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile)
  });
  return await res.json();
}

export async function resetDatabase() {
  const res = await fetch(`${API_BASE}/api/settings/reset-database`, { method: "POST" });
  return await res.json();
}

export async function getBeginnerGlossary() {
  const res = await fetch(`${API_BASE}/api/learning/glossary`, { cache: "no-store" });
  if (!res.ok) return { glossary: [] };
  return await res.json();
}

export async function getContributionSequence() {
  const res = await fetch(`${API_BASE}/api/learning/contribution-sequence`, { cache: "no-store" });
  if (!res.ok) return { sequence: [] };
  return await res.json();
}

export async function getRepositoryDocumentation(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repositories/${owner}/${repo}/documentation`, { cache: "no-store" });
  if (!res.ok) return null;
  return await res.json();
}

export async function generateRepositoryDocumentation(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repositories/${owner}/${repo}/generate-docs`, { method: "POST" });
  if (!res.ok) throw new Error("Documentation generation failed.");
  return await res.json();
}

export async function runModelBenchmark(model?: string) {
  const url = model ? `${API_BASE}/api/benchmark/run?model=${encodeURIComponent(model)}` : `${API_BASE}/api/benchmark/run`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error("Benchmark run failed.");
  return await res.json();
}

export async function getIssueInvestigation(owner: string, repo: string, number: number) {
  const res = await fetch(`${API_BASE}/api/issues/${owner}/${repo}/${number}/investigation`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load issue investigation.");
  return await res.json();
}

export async function getIssueTriage(owner: string, repo: string, number: number) {
  const res = await fetch(`${API_BASE}/api/issues/${owner}/${repo}/${number}/triage`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load issue triage.");
  return await res.json();
}

export async function saveIssueTriage(owner: string, repo: string, number: number, triageData: any) {
  const res = await fetch(`${API_BASE}/api/issues/${owner}/${repo}/${number}/triage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(triageData)
  });
  if (!res.ok) throw new Error("Failed to save triage notes.");
  return await res.json();
}

export async function addIssueHypothesis(owner: string, repo: string, number: number, data: any) {
  const res = await fetch(`${API_BASE}/api/issues/${owner}/${repo}/${number}/hypotheses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error("Failed to add hypothesis.");
  return await res.json();
}

export async function updateIssueHypothesisStatus(owner: string, repo: string, number: number, hypoId: string, status: string, uncertainty?: string) {
  const res = await fetch(`${API_BASE}/api/issues/${owner}/${repo}/${number}/hypotheses/${hypoId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, remaining_uncertainty: uncertainty })
  });
  if (!res.ok) throw new Error("Failed to update hypothesis.");
  return await res.json();
}

export async function getMaintainerDrafts(owner: string, repo: string, number: number) {
  const res = await fetch(`${API_BASE}/api/issues/${owner}/${repo}/${number}/maintainer-drafts`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load maintainer communication drafts.");
  return await res.json();
}

