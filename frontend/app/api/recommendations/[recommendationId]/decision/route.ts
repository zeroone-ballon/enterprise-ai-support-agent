import { NextRequest, NextResponse } from "next/server";

const RECOMMENDATION_ID = /^[A-Za-z0-9._-]{1,96}$/;

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ recommendationId: string }> },
) {
  const { recommendationId } = await context.params;
  if (!RECOMMENDATION_ID.test(recommendationId)) {
    return NextResponse.json({ detail: "Invalid recommendation ID." }, { status: 400 });
  }

  const apiKey = process.env.FASTAPI_REVIEWER_API_KEY;
  const reviewer = process.env.FASTAPI_REVIEWER_ACTOR ?? "service-desk-lead";
  if (!apiKey) {
    return NextResponse.json(
      { detail: "Reviewer credentials are not configured on the console server." },
      { status: 503 },
    );
  }

  try {
    const input: unknown = await request.json();
    if (
      typeof input !== "object" ||
      input === null ||
      !("decision" in input) ||
      (input.decision !== "approve" && input.decision !== "reject") ||
      !("reason" in input) ||
      typeof input.reason !== "string" ||
      !input.reason.trim()
    ) {
      return NextResponse.json(
        { detail: "Select approve or reject and provide a review reason." },
        { status: 400 },
      );
    }

    const baseUrl = process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(
      `${baseUrl.replace(/\/$/, "")}/recommendations/${encodeURIComponent(recommendationId)}/${input.decision}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({ reviewer, reason: input.reason.trim() }),
        cache: "no-store",
        signal: AbortSignal.timeout(10_000),
      },
    );
    const body: unknown = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json(
      { detail: "The review service is unavailable. Check that FastAPI is running." },
      { status: 502 },
    );
  }
}
