import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
  if (backendUrl && !backendUrl.includes("localhost") && !backendUrl.includes("127.0.0.1")) {
    try {
      const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/contributions`, {
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
    contributions: [
      {
        id: "contrib_demo_1",
        repo_id: "sukrut07/HacktoberDYP",
        title: "Setup space for Gemma 4 API key and Vercel full-stack deployment",
        status: "verified",
        current_step: "Verify & PR Draft",
        events_count: 8,
        proof_badge: "VERIFIED",
        created_at: new Date().toISOString()
      }
    ],
    count: 1
  });
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    return NextResponse.json({
      status: "created",
      id: `contrib_${Date.now()}`,
      ...body
    });
  } catch {
    return NextResponse.json({ status: "created", id: `contrib_${Date.now()}` });
  }
}
