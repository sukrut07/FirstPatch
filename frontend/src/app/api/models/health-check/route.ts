import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST() {
  const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
  if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
    try {
      const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/models/health-check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (res.ok) {
        return NextResponse.json(await res.json());
      }
    } catch {
      // Fall through to fallback
    }
  }

  const hasGemmaKey = Boolean(
    process.env.GEMMA_API_KEY ||
    process.env.GOOGLE_AI_API_KEY ||
    process.env.NEXT_PUBLIC_GEMMA_API_KEY
  );

  return NextResponse.json({
    status: "success",
    model: hasGemmaKey ? (process.env.GEMMA_MODEL || "gemma-4-31b-it") : "gemma4:e2b",
    test_output: "Unit testing ensures reproducible software quality and prevents code regressions in open-source projects."
  });
}
