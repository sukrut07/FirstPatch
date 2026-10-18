import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({
    local_inference_default: true,
    external_network_requests: [
      "GitHub REST API (public metadata & open issues)",
      "Local Ollama API (http://127.0.0.1:11434)",
      "Google AI Studio / Gemma 4 (Optional user-supplied key)"
    ],
    telemetry_enabled: false,
    storage_mode: "Local SQLite (WAL mode) / Browser LocalStorage",
    security_sandbox: "Subprocess with timeout, environment sanitation & resource bounds"
  });
}
