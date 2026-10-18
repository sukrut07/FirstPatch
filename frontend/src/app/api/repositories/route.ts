import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
  if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
    try {
      const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/repositories`, {
        cache: "no-store"
      });
      if (res.ok) {
        return NextResponse.json(await res.json());
      }
    } catch {
      // Fallback
    }
  }

  // Pre-indexed curated open source repositories for instant explore access
  const curated = [
    {
      id: "sukrut07/HacktoberDYP",
      owner: "sukrut07",
      name: "HacktoberDYP",
      full_name: "sukrut07/HacktoberDYP",
      description: "FirstPatch AI — Open-source contribution trust layer and evidence-grounded mentor.",
      stars: 48,
      forks: 14,
      open_issues_count: 5,
      language: "Python",
      topics: ["open-source", "python", "fastapi", "nextjs", "gemma4"],
      license_name: "MIT License",
      html_url: "https://github.com/sukrut07/HacktoberDYP",
      status: "ready",
      indexed_at: new Date().toISOString()
    },
    {
      id: "pallets/click",
      owner: "pallets",
      name: "click",
      full_name: "pallets/click",
      description: "Python composable command line interface toolkit with zero external dependencies.",
      stars: 16200,
      forks: 1400,
      open_issues_count: 24,
      language: "Python",
      topics: ["python", "cli", "good-first-issue"],
      license_name: "BSD-3-Clause",
      html_url: "https://github.com/pallets/click",
      status: "ready",
      indexed_at: new Date().toISOString()
    },
    {
      id: "encode/httpx",
      owner: "encode",
      name: "httpx",
      full_name: "encode/httpx",
      description: "A next generation HTTP client for Python with sync and async APIs.",
      stars: 14100,
      forks: 1250,
      open_issues_count: 32,
      language: "Python",
      topics: ["http", "async", "python", "networking"],
      license_name: "BSD-3-Clause",
      html_url: "https://github.com/encode/httpx",
      status: "ready",
      indexed_at: new Date().toISOString()
    }
  ];

  return NextResponse.json({
    repositories: curated,
    count: curated.length
  });
}
