import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
  if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
    try {
      const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/models/status`, {
        cache: "no-store"
      });
      if (res.ok) {
        return NextResponse.json(await res.json());
      }
    } catch {
      // Fallback to edge status
    }
  }

  const hasGemmaKey = Boolean(
    process.env.GEMMA_API_KEY ||
    process.env.GOOGLE_AI_API_KEY ||
    process.env.NEXT_PUBLIC_GEMMA_API_KEY
  );

  return NextResponse.json({
    online: hasGemmaKey,
    active_model: hasGemmaKey ? (process.env.GEMMA_MODEL || "gemma-4-31b-it") : "gemma4:e2b",
    embed_model: "nomic-embed-text",
    installed_models: hasGemmaKey ? ["gemma-4-31b-it (Google AI Studio)", "gemma4:e2b", "gemma2:2b"] : ["gemma4:e2b", "gemma2:2b"],
    cloud_gemma_configured: hasGemmaKey,
    provider: hasGemmaKey ? "google_ai_studio" : "ollama_local",
    timestamp: new Date().toISOString()
  });
}
