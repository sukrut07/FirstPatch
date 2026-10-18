import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
  if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
    try {
      const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/models`, {
        cache: "no-store"
      });
      if (res.ok) {
        return NextResponse.json(await res.json());
      }
    } catch {
      // Fallback
    }
  }

  const hasGemmaKey = Boolean(
    process.env.GEMMA_API_KEY ||
    process.env.GOOGLE_AI_API_KEY ||
    process.env.NEXT_PUBLIC_GEMMA_API_KEY
  );

  return NextResponse.json({
    installed_models: [
      "gemma-4-31b-it",
      "gemma-4-26b",
      "gemma-2-9b-it",
      "gemma4:e2b",
      "gemma2:2b"
    ],
    active_model: hasGemmaKey ? (process.env.GEMMA_MODEL || "gemma-4-31b-it") : "gemma4:e2b",
    embed_model: "nomic-embed-text"
  });
}
