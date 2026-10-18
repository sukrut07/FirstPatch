import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ owner: string; repo: string }> }
) {
  const { owner, repo } = await params;
  const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;

  if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
    try {
      const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/repositories/${owner}/${repo}/architecture`, {
        cache: "no-store"
      });
      if (res.ok) {
        return NextResponse.json(await res.json());
      }
    } catch {
      // Fallback
    }
  }

  return NextResponse.json({
    repo_id: `${owner}/${repo}`,
    entry_points: ["main.py", "app.py", "src/index.ts", "package.json"],
    core_modules: [
      { name: "API Layer", path: "routers / controllers", desc: "Handles external HTTP requests and payload validation." },
      { name: "Business Logic", path: "services / lib", desc: "Deterministic logic, state management, and orchestration." },
      { name: "Data Access", path: "database / models", desc: "Persistence, schema models, and data access layers." }
    ],
    mermaid_diagram: `graph TD
  User([Contributor]) --> Frontend[Next.js Web Interface]
  Frontend --> API[API Endpoints]
  API --> Orchestrator[Evidence Orchestrator]
  Orchestrator --> AST[AST & Syntax Parser]
  Orchestrator --> Reality[Reality Checker & Sandbox]
  Orchestrator --> LLM[Gemma 4 AI Assistant]
  Reality --> Output([Verified PR Plan])`
  });
}
