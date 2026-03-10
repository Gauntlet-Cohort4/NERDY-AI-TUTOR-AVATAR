import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "healthy",
    service: "nerdy-ai-tutor-frontend",
    timestamp: new Date().toISOString(),
  });
}
