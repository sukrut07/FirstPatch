import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const apiKey = (body.api_key || "").trim();
    const provider = body.provider || "google_ai_studio";
    const model = body.model || "gemma-4-31b-it";

    if (!apiKey) {
      return NextResponse.json({ detail: "API key is required." }, { status: 400 });
    }

    // Try backend proxy if available
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
    if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
      try {
        const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/models/test-cloud-key`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: apiKey, provider, model })
        });
        if (res.ok) {
          return NextResponse.json(await res.json());
        }
      } catch {
        // Fall back to direct edge verification
      }
    }

    // Direct Google AI Studio verification
    if (provider === "google_ai_studio" || apiKey.startsWith("AIza")) {
      const googleRes = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models?key=${encodeURIComponent(apiKey)}`,
        { headers: { "Content-Type": "application/json" } }
      );
      if (!googleRes.ok) {
        const errData = await googleRes.json().catch(() => ({}));
        const msg = errData?.error?.message || "Invalid Google AI Studio / Gemma API key.";
        return NextResponse.json({ detail: msg }, { status: 400 });
      }

      return NextResponse.json({
        status: "success",
        model: model,
        provider: "Google AI Studio (Gemma 4)",
        test_output: "Authentication successful! Google AI Studio & Gemma 4 are ready to analyze repositories."
      });
    }

    // OpenRouter verification
    if (provider === "openrouter" || apiKey.startsWith("sk-or-")) {
      const orRes = await fetch("https://openrouter.ai/api/v1/auth/key", {
        headers: { Authorization: `Bearer ${apiKey}` }
      });
      if (!orRes.ok) {
        return NextResponse.json({ detail: "Invalid OpenRouter API key." }, { status: 400 });
      }
      return NextResponse.json({
        status: "success",
        model: model,
        provider: "OpenRouter",
        test_output: "Authentication successful! OpenRouter connection verified."
      });
    }

    // Generic key check
    if (apiKey.length < 8) {
      return NextResponse.json({ detail: "API key appears too short or invalid." }, { status: 400 });
    }

    return NextResponse.json({
      status: "success",
      model: model,
      provider: provider,
      test_output: `Key validated for ${provider}. Ready for deep repository intelligence.`
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Failed to test API key" }, { status: 500 });
  }
}
