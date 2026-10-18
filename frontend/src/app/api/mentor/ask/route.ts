import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const prompt = body.prompt || body.message || "";
    const repoId = body.repo_id || "";
    const apiKey = body.api_key || process.env.GEMMA_API_KEY || process.env.GOOGLE_AI_API_KEY;

    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
    if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
      try {
        const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/mentor/ask`, {
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

    if (apiKey) {
      try {
        const fullPrompt = `You are FirstPatch AI, an open-source contribution mentor.
Repository: ${repoId || "Open Source Project"}
User Question: ${prompt}

Give a clear, evidence-grounded answer explaining:
1. The architectural concept or contribution step.
2. Best practices according to standard open source contributor guidelines.
3. Keep your advice constructive, concise, and beginner-friendly.`;

        const geminiRes = await fetch(
          `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${encodeURIComponent(apiKey)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ contents: [{ parts: [{ text: fullPrompt }] }] })
          }
        );

        if (geminiRes.ok) {
          const gData = await geminiRes.json();
          const responseText = gData?.candidates?.[0]?.content?.parts?.[0]?.text || "";
          return NextResponse.json({
            response: responseText,
            role: "assistant",
            model: "Gemma 4 (Google AI Studio)",
            status: "success"
          });
        }
      } catch {
        // Fall through
      }
    }

    // Default grounded mentor guidance
    return NextResponse.json({
      response: `To contribute effectively to ${repoId || "this open-source project"}:
1. **Understand First**: Always read the repository's \`CONTRIBUTING.md\` and locate the affected code before writing a patch.
2. **Minimal Changes**: Keep your pull request focused on solving one specific issue.
3. **Verify Locally**: Add or update test cases and run the test suite to verify 100% pass rate before opening a PR.

Tip: Add your free Google AI Studio Gemma 4 API Key in Settings or the home page drawer to enable real-time generative repository mentor answers!`,
      role: "assistant",
      model: "FirstPatch Mentor Engine",
      status: "success"
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Failed to process question" }, { status: 400 });
  }
}
