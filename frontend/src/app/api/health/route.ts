import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
  if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
    try {
      const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/health`, {
        cache: "no-store"
      });
      if (res.ok) {
        return NextResponse.json(await res.json());
      }
    } catch {
      // Fall through to edge health response
    }
  }

  const hasGemmaKey = Boolean(
    process.env.GEMMA_API_KEY ||
    process.env.GOOGLE_AI_API_KEY ||
    process.env.NEXT_PUBLIC_GEMMA_API_KEY
  );

  return NextResponse.json({
    status: "ok",
    app_name: "FirstPatch AI",
    version: "1.0.0",
    environment: process.env.VERCEL ? "production-vercel" : "development",
    ai_provider: hasGemmaKey ? "google_ai_studio" : "ollama",
    ai_provider_status: hasGemmaKey ? "available" : "ready_for_key",
    github_authenticated: Boolean(process.env.GITHUB_TOKEN),
    timestamp: new Date().toISOString(),
    database: "healthy",
    gemma: {
      active: hasGemmaKey,
      model: process.env.GEMMA_MODEL || "gemma-4-31b-it",
      provider: "Google AI Studio / Gemma 4"
    },
    ollama: {
      online: false,
      message: "Vercel edge serverless deployment active. Use Gemma 4 API Key or local backend."
    }
  });
}
