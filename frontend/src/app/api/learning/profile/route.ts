import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({
    id: "default",
    skill_level: "Beginner",
    preferred_languages: ["Python", "TypeScript"],
    interests: ["Web", "DevTools"],
    learning_goals: "Make my first verified open source contribution",
    completed_drills_count: 0
  });
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json();
    return NextResponse.json({ status: "updated", profile: body });
  } catch {
    return NextResponse.json({ status: "updated" });
  }
}
