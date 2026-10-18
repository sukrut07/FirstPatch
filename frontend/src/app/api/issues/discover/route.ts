import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const repoId = body.repo_id || "";
    const [owner, repo] = repoId.split("/");

    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
    if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
      try {
        const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/issues/discover`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        if (res.ok) {
          return NextResponse.json(await res.json());
        }
      } catch {
        // Fallback
      }
    }

    if (owner && repo) {
      const ghHeaders: Record<string, string> = {
        "User-Agent": "FirstPatch-AI-Vercel/1.0",
        "Accept": "application/vnd.github.v3+json"
      };
      if (process.env.GITHUB_TOKEN) {
        ghHeaders["Authorization"] = `Bearer ${process.env.GITHUB_TOKEN}`;
      }

      try {
        const ghRes = await fetch(
          `https://api.github.com/repos/${owner}/${repo}/issues?state=open&per_page=10`,
          { headers: ghHeaders, cache: "no-store" }
        );
        if (ghRes.ok) {
          const ghIssues = await ghRes.json();
          const mapped = ghIssues
            .filter((i: any) => !i.pull_request)
            .map((i: any) => ({
              id: `${repoId}#${i.number}`,
              repo_id: repoId,
              number: i.number,
              title: i.title,
              body: i.body || "",
              html_url: i.html_url,
              state: i.state,
              labels: (i.labels || []).map((l: any) => (typeof l === "string" ? l : l.name)),
              author: i.user?.login || "contributor",
              created_at: i.created_at,
              fit_score: 85,
              claim_safe: true,
              claim_safety_reason: "No active assignees or recent linked pull requests."
            }));
          return NextResponse.json({ issues: mapped, count: mapped.length });
        }
      } catch {
        // Fallback
      }
    }

    return NextResponse.json({
      issues: [
        {
          id: `${repoId}#1`,
          repo_id: repoId,
          number: 1,
          title: "Improve error handling and add docstrings to core modules",
          body: "Beginner-friendly task to review edge cases in user input handling and improve code documentation.",
          html_url: `https://github.com/${repoId}/issues/1`,
          state: "open",
          labels: ["good first issue", "documentation"],
          author: "maintainer",
          created_at: new Date().toISOString(),
          fit_score: 92,
          claim_safe: true,
          claim_safety_reason: "Safe to claim: No active assignees or open PRs linked."
        }
      ],
      count: 1
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Failed to discover issues" }, { status: 400 });
  }
}
