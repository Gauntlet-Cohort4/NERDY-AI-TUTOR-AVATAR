import { NextResponse } from "next/server";

const VALID_SUBJECTS = new Set(["biology", "math", "physics"]);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const subject = searchParams.get("subject") ?? "biology";

  if (!VALID_SUBJECTS.has(subject)) {
    return NextResponse.json(
      { error: `Invalid subject. Must be one of: ${[...VALID_SUBJECTS].join(", ")}` },
      { status: 400 }
    );
  }

  const token = process.env.LIVEKIT_TOKEN ?? "";
  const url = process.env.NEXT_PUBLIC_LIVEKIT_URL ?? "";

  // Health check: warn but still return so the UI can surface the misconfiguration.
  const healthy = Boolean(token && url);

  return NextResponse.json(
    {
      token,
      url,
      subject,
      healthy,
      ...(healthy ? {} : { warning: "LIVEKIT_TOKEN or NEXT_PUBLIC_LIVEKIT_URL is not configured" }),
    },
    { status: 200 }
  );
}
