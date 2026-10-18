import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ owner: string; repo: string }> }
) {
  try {
    const { owner, repo } = await params;
    const body = await req.json().catch(() => ({}));
    const apiKey = body.api_key || process.env.GEMMA_API_KEY || process.env.GOOGLE_AI_API_KEY;
    const model = body.model || process.env.GEMMA_MODEL || "gemma-4-31b-it";

    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
    if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
      try {
        const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/repositories/${owner}/${repo}/analyze-ai`, {
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

    if (!apiKey) {
      return NextResponse.json({
        detail: "Gemma 4 API key is required. Please provide a Google AI Studio or Gemma key in the header or settings."
      }, { status: 400 });
    }

    // Call Google AI Studio / Gemini API with Gemma 4 or Gemini 1.5 Flash
    const prompt = `You are FirstPatch AI, an open-source contribution mentor. Analyze repository "${owner}/${repo}".
Provide structured JSON with:
1. "executive_summary": Overview for first-time contributors
2. "beginner_friendly_zones": Array of 3 specific starter areas
3. "setup_gotchas": Array of 2 common environment pitfalls
4. "contribution_recommendation": Advice on picking an issue

Format strictly as JSON.`;

    const geminiRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${encodeURIComponent(apiKey)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
      }
    );

    if (!geminiRes.ok) {
      const err = await geminiRes.json().catch(() => ({}));
      return NextResponse.json({ detail: err?.error?.message || "Gemma 4 inference failed." }, { status: 400 });
    }

    const gData = await geminiRes.json();
    const rawText = gData?.candidates?.[0]?.content?.parts?.[0]?.text || "{}";
    const jsonMatch = rawText.match(/\{[\s\S]*\}/);
    let parsed: any = {};
    if (jsonMatch) {
      parsed = JSON.parse(jsonMatch[0]);
    }

    parsed.model_used = model;
    parsed.provider_used = "Google AI Studio / Gemma 4";
    parsed.analyzed_at = new Date().toISOString();

    return NextResponse.json({
      status: "success",
      ai_analysis: parsed
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Failed to analyze repository with Gemma 4" }, { status: 500 });
  }
}
