import { NextRequest, NextResponse } from "next/server";

const SAFE_ID = /^[A-Za-z0-9._-]{1,96}$/;
const SAFE_KEY = /^[A-Za-z0-9._:-]{8,128}$/;

export async function POST(request: NextRequest, context: { params: Promise<{ recommendationId: string }> }) {
  const { recommendationId } = await context.params;
  const apiKey = process.env.FASTAPI_EXECUTOR_API_KEY;
  const executor = process.env.FASTAPI_EXECUTOR_ACTOR ?? "automation-operator";
  if (!SAFE_ID.test(recommendationId)) return NextResponse.json({ detail: "Invalid recommendation ID." }, { status: 400 });
  if (!apiKey) return NextResponse.json({ detail: "Executor credentials are not configured on the console server." }, { status: 503 });
  try {
    const input: unknown = await request.json();
    const key = typeof input === "object" && input !== null && "idempotencyKey" in input && typeof input.idempotencyKey === "string" ? input.idempotencyKey : "";
    if (!SAFE_KEY.test(key)) return NextResponse.json({ detail: "Invalid idempotency key." }, { status: 400 });
    const baseUrl = process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/recommendations/${encodeURIComponent(recommendationId)}/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey, "Idempotency-Key": key },
      body: JSON.stringify({ executor }), cache: "no-store", signal: AbortSignal.timeout(15_000),
    });
    const body: unknown = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json({ detail: "The execution service is unavailable." }, { status: 502 });
  }
}
