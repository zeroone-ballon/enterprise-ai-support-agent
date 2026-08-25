import { NextResponse } from "next/server";

const SAFE_ID = /^[A-Za-z0-9._-]{1,96}$/;

export async function GET(_request: Request, context: { params: Promise<{ recommendationId: string }> }) {
  const { recommendationId } = await context.params;
  const apiKey = process.env.FASTAPI_AUDITOR_API_KEY;
  if (!SAFE_ID.test(recommendationId)) return NextResponse.json({ detail: "Invalid recommendation ID." }, { status: 400 });
  if (!apiKey) return NextResponse.json({ detail: "Auditor credentials are not configured on the console server." }, { status: 503 });
  try {
    const baseUrl = process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/recommendations/${encodeURIComponent(recommendationId)}/audit`, {
      headers: { "X-API-Key": apiKey }, cache: "no-store", signal: AbortSignal.timeout(10_000),
    });
    const body: unknown = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json({ detail: "The audit service is unavailable." }, { status: 502 });
  }
}
