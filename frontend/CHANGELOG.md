# Changelog — Frontend (Next.js)

All notable changes to the frontend will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Phase 5] - 2026-03-11

### Added
- Code cleanup and consistent formatting

### Changed
- Wrapped `useSearchParams()` in a Suspense boundary to fix Next.js App Router requirement
- Updated latency table display for consistency

### Decisions
- Playwright E2E tests deferred to a future phase; documented in root README as a known limitation

## [Phase 4] - 2026-03-09

### Added
- `frontend/Dockerfile` — Node 20 image with Next.js standalone build and health check
- ESLint configuration (`eslint.config.mjs`) for CI linting
- `package-lock.json` committed for reproducible CI builds
- CI pipeline job `lint-frontend` running tsc and eslint

### Changed
- Docker build target switched to Next.js standalone output for smaller image size

## [Phase 3] - 2026-03-09

### Added
- `app/page.tsx` — home page with `SubjectSelector` component; navigates to `/session?subject={subject}`
- `app/session/page.tsx` — session page wrapping `LiveKitRoom` with avatar display, latency overlay, and connection status
- `app/session/SessionInner.tsx` — hook bridge component rendered inside `<LiveKitRoom>` context; syncs `useConnectionState()` and `useDataChannel("metrics")` to parent-managed state; renders `null` (purely a hook bridge)
- `components/AvatarDisplay.tsx` — renders remote video track from LiveKit; shows animated SVG avatar silhouette as fallback when no video track is active
- `components/LatencyOverlay.tsx` — real-time per-stage latency display (STT, LLM TTFT, TTS TTFB, Avatar, Total E2E) from data channel metrics published by the agent
- `components/SubjectSelector.tsx` — subject picker with Biology, Math, and Physics cards
- `components/SessionControls.tsx` — connect/disconnect button controls
- `components/ConnectionStatus.tsx` — WebRTC connection state indicator
- `app/api/token/route.ts` — GET endpoint generating LiveKit JWTs with subject validation; creates room name `tutor-{subject}-{timestamp}` matching the agent's `_resolve_agent()` parser
- `app/api/health/route.ts` — GET endpoint returning service health status
- `lib/livekit.ts` — LiveKit client utilities: `fetchToken()`, `mapConnectionState()`, `parseMetricsMessage()` for data channel JSON parsing
- `app/globals.css` — Tailwind CSS with custom component classes for avatar container

### Decisions
- **`SessionInner` renders `null`** — it is purely a hook bridge that must live inside `<LiveKitRoom>` context. All visual rendering is handled by sibling components to maintain separation of concerns.
- **Room name convention `tutor-{subject}-{timestamp}`** matches the agent's `_resolve_agent()` parser, enabling direct subject routing without a router greeting round-trip.
- **`useSearchParams()` requires Suspense** in Next.js App Router; the session page wraps the relevant component in a `<Suspense>` boundary.

## [Phase 0] - 2026-03-09

### Added
- Next.js 14 project scaffold with TypeScript and Tailwind CSS
- `package.json` with Next.js 14, `@livekit/components-react`, `livekit-client`, Tailwind CSS, Playwright dependencies
- `lib/logger.ts` — structured JSON frontend logger matching the backend's structlog format
- `lib/types.ts` — TypeScript type contracts: `ConnectionState`, `TurnMetrics`, `SessionConfig`, `Subject`
- Component stubs: `AvatarDisplay`, `LatencyOverlay`, `SubjectSelector`, `SessionControls`, `ConnectionStatus`
- Page stubs: landing page, session page
- Health check API at `/api/health`
- `playwright.config.ts` — Playwright test configuration (Chromium)
- `next.config.js`, `tailwind.config.ts`, `tsconfig.json` — framework configuration
- `Dockerfile` with health check

### Decisions
- **TypeScript target set to `es2017+`** to support Set iteration and other modern JS features without transpilation issues.
- **Next.js only reads `.env` from its own directory** — environment variables must be in `frontend/.env.local`, not the root `.env`. This is a Next.js convention, not a project choice.
