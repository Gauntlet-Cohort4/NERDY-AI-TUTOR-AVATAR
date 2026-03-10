# Changelog — Frontend

## [Phase 0] - 2026-03-09

### Added
- Next.js 14 project scaffold with TypeScript and Tailwind CSS
- `lib/logger.ts` — structured JSON logger matching backend format
- `lib/types.ts` — TypeScript contracts (Subject, TurnMetrics, SessionSummary, ConnectionState)
- Component stubs: AvatarDisplay, LatencyOverlay, SubjectSelector, SessionControls, ConnectionStatus
- Page stubs: landing page, session page
- Health check API at `/api/health`
- Playwright config for E2E testing (Chromium)
- package.json with LiveKit, React, Next.js dependencies
- Dockerfile with health check
