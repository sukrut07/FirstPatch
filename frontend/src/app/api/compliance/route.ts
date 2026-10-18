import { NextResponse } from "next/server";
import { GET as getReport } from "./report/route";

export const runtime = "nodejs";

export async function GET() {
  return getReport();
}
