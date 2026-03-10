# Changelog — Frontend

## [Phase 3] - 2026-03-09

### Added
- `lib/livekit.ts` — LiveKit client utilities:
  - `mapConnectionState()` — maps `ConnectionState` enum to user-friendly `ConnectionStatus` strings
  - `fetchToken()` — fetches a LiveKit access token from `/api/token` with subject and participant name
  - `parseMetrics()` — parses `TurnMetrics` JSON from the LiveKit data channel for real-time latency display
- `app/page.tsx` — Home page with `SubjectSelector` component and navigation to `/session?subject=<value>`
- `app/session/page.tsx` — Full session page:
  - Reads `?subject=` query parameter and validates against `Subject` enum
  - Renders `LiveKitRoom` (auto-connect, video disabled by default)
  - Shows `AvatarDisplay`, `LatencyOverlay`, `ConnectionStatus`, and `SessionControls`
  - Handles disconnect and back-navigation
- `app/session/SessionInner.tsx` — Bridge component rendered inside `LiveKitRoom` context:
  - Uses `useRemoteTracks()` to bind the first remote video track to `AvatarDisplay`
  - Uses `useDataChannel()` to receive `TurnMetrics` JSON published by the agent
  - Forwards metrics state up to the parent session page
- `components/AvatarDisplay.tsx` — Remote video track rendering:
  - Attaches a `RemoteVideoTrack` to a `<video>` element via ref + `track.attach()`
  - Shows an animated SVG avatar silhouette as fallback when no video track is active
- `app/api/token/route.ts` — Token API endpoint (`GET /api/token`):
  - Validates `subject` and `participantName` query parameters
  - Generates a LiveKit `AccessToken` with `RoomJoin` + `RoomCreate` grants
  - Returns `{ token }` JSON; returns 400 on missing or invalid params
- `app/globals.css` — Custom Tailwind component classes: `.avatar-container`, `.avatar-video`

## [Phase 0] - 2026-03-09

### Added
- Next.js 14 project scaffold with TypeScript and Tailwind CSS
- `lib/logger.ts` — structured JSON logger matching backend format
- `lib/types.ts` — TypeScript contracts (`Subject`, `TurnMetrics`, `SessionSummary`, `ConnectionState`)
- Component stubs: `AvatarDisplay`, `LatencyOverlay`, `SubjectSelector`, `SessionControls`, `ConnectionStatus`
- Page stubs: landing page, session page
- Health check API at `/api/health`
- Playwright config for E2E testing (Chromium)
- `package.json` with LiveKit, React, Next.js, and Tailwind dependencies
- `Dockerfile` with health check
