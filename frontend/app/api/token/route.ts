import { NextResponse } from "next/server";
import { AccessToken } from "livekit-server-sdk";

const VALID_SUBJECTS = new Set([
  "biology",
  "math",
  "earth_science",
  "intro_algebra",
  "algebra_ii",
  "chemistry",
  "cell_biology",
  "world_history",
  "calculus",
  "physics",
  "ap_biology",
]);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const subject = searchParams.get("subject") ?? "biology";
  const gradeRaw = searchParams.get("grade");
  const grade = gradeRaw && /^([6-9]|1[0-2])$/.test(gradeRaw) ? gradeRaw : null;

  if (!VALID_SUBJECTS.has(subject)) {
    return NextResponse.json(
      { error: `Invalid subject. Must be one of: ${[...VALID_SUBJECTS].join(", ")}` },
      { status: 400 }
    );
  }

  const apiKey = process.env.LIVEKIT_API_KEY ?? "";
  const apiSecret = process.env.LIVEKIT_API_SECRET ?? "";
  const livekitUrl = process.env.LIVEKIT_URL ?? "";

  if (!apiKey || !apiSecret || !livekitUrl) {
    return NextResponse.json(
      {
        error: "Server misconfigured",
        warning: "LIVEKIT_API_KEY, LIVEKIT_API_SECRET, or LIVEKIT_URL is not set",
        healthy: false,
      },
      { status: 503 }
    );
  }

  const roomName = grade
    ? `tutor-${subject}-g${grade}-${Date.now()}`
    : `tutor-${subject}-${Date.now()}`;
  const participantIdentity = `student-${Date.now()}`;

  const token = new AccessToken(apiKey, apiSecret, {
    identity: participantIdentity,
    name: "Student",
  });
  token.addGrant({
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canSubscribe: true,
  });

  const jwt = await token.toJwt();

  return NextResponse.json({
    token: jwt,
    url: livekitUrl,
    subject,
    room: roomName,
    identity: participantIdentity,
    healthy: true,
  });
}
