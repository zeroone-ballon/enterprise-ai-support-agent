import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const baseUrl = process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const incident: unknown = await request.json();
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/assist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(incident),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    const body: unknown = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json(
      { detail: "The local support API is unavailable. Check that FastAPI is running." },
      { status: 502 },
    );
  }
}
