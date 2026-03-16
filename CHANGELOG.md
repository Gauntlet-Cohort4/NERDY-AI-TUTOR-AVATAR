# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [Phase 9] - 2026-03-16

### Added
- `DECISIONS.md` — comprehensive architectural and design decision log
- `OPTIMIZATION.md` — per-stage pipeline optimization strategies with reasoning
- `LIMITATIONS.md` — known limitations, failure modes, and edge cases
- `COST_ANALYSIS.md` — infrastructure cost analysis and scaling projections (100 to 100K users)
- `agent/src/artifacts/pdf_renderer.py` — on-demand PDF rendering using fpdf2 with Unicode font support
- `frontend/app/reviews/[sessionId]/flash-cards/page.tsx` — dedicated flash cards study page with mastery tracking
- Auto-generate flash cards when visiting a session that has none
- react-markdown + @tailwindcss/typography for rendered markdown summaries
- KaTeX rendering for LaTeX math formulas in cheat sheets

### Changed
- Replaced WeasyPrint with fpdf2 for PDF generation (fixes `transform` AttributeError in WeasyPrint 62.3)
- Summary and Cheat Sheet buttons on reviews list now navigate to session detail page (removed inline expand)
- Cheat Sheet link scrolls to `#cheat-sheet` anchor on session detail page
- Flash Cards button links directly to `/reviews/[sessionId]/flash-cards`
- Updated README with latency benchmarks, documentation links, updated project structure, and cost analysis
- Updated avatar provider documentation to reflect Beyond Presence as primary provider

## [Phase 5] - 2026-03-09

### Added
- `CLAUDE.md` — project-level instructions for Claude Code (tech stack, commands, conventions)

### Changed
- Updated root `README.md` to reflect all implemented phases and current project state
- Updated `CHANGELOG.md` files (root, agent, frontend) with entries for all phases

## [Phase 4] - 2026-03-09

### Added
- `docker-compose.yml` — full-stack Docker Compose configuration for agent + frontend services
- `agent/Dockerfile` — multi-stage Python 3.11 image with health check
- `frontend/Dockerfile` — Node 20 image with Next.js build and health check
- `.github/workflows/ci.yml` — CI pipeline: lint (ruff, tsc, eslint) + unit tests on every PR
- `.github/workflows/integration.yml` — integration test workflow (manual trigger + nightly)
- `scripts/lint.sh` — unified lint script (ruff, tsc, eslint)
- `scripts/list-voices.py` — Cartesia voice listing utility
- `scripts/list-faces.py` — Simli face listing utility

## [Phase 3] - 2026-03-09

### Added
- `frontend/lib/livekit.ts` — LiveKit client utilities: connection state mapping, token fetching, metrics parsing from data channel
- `frontend/app/page.tsx` — Home page with SubjectSelector and navigation to `/session`
- `frontend/app/session/page.tsx` — Full session page with LiveKitRoom, avatar display, latency overlay, and connection status
- `frontend/app/session/SessionInner.tsx` — Bridge component for LiveKit hooks inside room context; wires remote tracks and data channel metrics
- `frontend/components/AvatarDisplay.tsx` — Remote video track rendering with SVG animated fallback
- `frontend/app/api/token/route.ts` — Token API endpoint with subject validation and LiveKit token generation
- `frontend/app/globals.css` — Custom Tailwind component classes for avatar container

## [Phase 2] - 2026-03-09

### Added
- `agent/main.py` — LiveKit AgentServer entrypoint with full STT → LLM → TTS pipeline wiring
- `agent/main.py` — `create_agent_session()` pure function for testable pipeline config
- `agent/main.py` — `health_check()` HTTP endpoint for the agent service
- `agent/src/avatar/renderer.py` — Full `SimliAvatarAdapter` implementation wrapping `livekit.plugins.simli` with graceful degradation when plugin is unavailable
- `agent/tests/unit/test_main.py` — Tests for entrypoint and session wiring (52 new tests)
- `agent/tests/unit/test_simli_adapter.py` — Tests for SimliAvatarAdapter (69 new tests)
- 122 tests total at 88% coverage

## [Phase 1] - 2026-03-09

### Added
- `agent/src/education/prompts.py` — Socratic system prompts for Biology (7th grade photosynthesis), Math (6th grade fractions), Physics (9th grade Newton's Third Law); enforces 2-sentence response rule and no-direct-answers policy
- `agent/src/education/subjects.py` — `SUBJECT_CONFIGS` dict mapping each `Subject` enum to a `SubjectConfig`; domain keyterms tuples for Deepgram Nova-3 STT accuracy
- `agent/src/education/history.py` — Fully immutable `ConversationHistory` (frozen dataclass); `add_turn()` returns a new instance; `get_context_window()` respects token budget (4 chars/token); async `summarize()` keeps recent turns and summarises older ones via injected `llm_callable`; `to_chat_context()` maps student→user, tutor→assistant
- `agent/src/agents/biology.py` — `BiologyTutorAgent(Agent)` with photosynthesis system prompt
- `agent/src/agents/math.py` — `MathTutorAgent(Agent)` with fractions system prompt
- `agent/src/agents/physics.py` — `PhysicsTutorAgent(Agent)` with Newton's Third Law system prompt
- `agent/src/agents/router.py` — `SubjectRouterAgent(Agent)` that greets the student; three `@function_tool` methods (`select_biology`, `select_math`, `select_physics`) call `session.update_agent()` to hand off to the appropriate subject tutor
- 77 new tests (106 total) at 92% coverage

## [Phase 0] - 2026-03-09

### Added
- Repository structure with all directories and placeholder files
- `agent/src/config.py` — central config loader with env var validation and fail-fast
- `agent/src/logging_setup.py` — structured logging with structlog (JSON output)
- `agent/src/errors.py` — `PipelineError` types, Socratic fallback responses, retry budgets
- `agent/src/types.py` — shared types, protocols, dataclasses (`Subject`, `TurnMetrics`, etc.)
- `agent/src/metrics.py` — `MetricsCollector` for per-turn latency events and session summary stats
- `agent/src/avatar/renderer.py` — `AvatarRenderer` protocol + `SimliAvatarAdapter` skeleton
- `agent/pyproject.toml` + `requirements.txt` with pinned Python dependencies
- `frontend/package.json` with Next.js 14, LiveKit, Playwright dependencies
- `frontend/lib/logger.ts` — frontend structured logger matching backend format
- `frontend/lib/types.ts` — TypeScript type contracts for cross-boundary data
- Frontend component stubs: `AvatarDisplay`, `LatencyOverlay`, `SubjectSelector`, `SessionControls`, `ConnectionStatus`
- Frontend health check API at `/api/health`
- `.env.example` with all required and optional variables documented
- `.github/workflows/ci.yml` — lint + test pipeline for PRs
- `.github/workflows/integration.yml` — integration tests (manual/nightly)
- `pytest.ini`, `.coveragerc`, `playwright.config.ts` — test configuration
- `docker-compose.yml` with agent + frontend services
- `Dockerfile` for agent (Python 3.11) and frontend (Node 20) with health checks
- `scripts/lint.sh` — runs ruff + tsc + eslint
- Root `README.md` with setup, architecture, and env var documentation
- Unit tests: `test_config`, `test_errors`, `test_metrics`, `test_avatar` (29 tests)
