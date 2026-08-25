import { NextRequest, NextResponse } from "next/server";

const INCIDENT_NUMBER = /^[A-Za-z0-9._-]{1,64}$/;

export async function POST(
  _request: NextRequest,
  context: { params: Promise<{ incidentNumber: string }> },
) {
  const { incidentNumber } = await context.params;
  if (!INCIDENT_NUMBER.test(incidentNumber)) {
    return NextResponse.json({ detail: "Enter a valid Incident number." }, { status: 400 });
  }

  const baseUrl = process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const response = await fetch(
      `${baseUrl.replace(/\/$/, "")}/assist/servicenow/${encodeURIComponent(incidentNumber)}`,
      { method: "POST", cache: "no-store", signal: AbortSignal.timeout(15_000) },
    );
    const body: unknown = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json(
      { detail: "The support API is unavailable. Check that FastAPI is running." },
      { status: 502 },
    );
  }
}
