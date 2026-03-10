# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Phase 0] - 2026-03-09

### Added
- Repository structure with all directories and placeholder files
- `src/config.py` — central config loader with env var validation and fail-fast
- `src/logging_setup.py` — structured logging with structlog (JSON output)
- `src/errors.py` — PipelineError types, Socratic fallback responses, retry budgets
- `src/types.py` — shared types, protocols, dataclasses (Subject, TurnMetrics, etc.)
- `src/metrics.py` — MetricsCollector for AgentSession latency events
- `src/avatar/renderer.py` — AvatarRenderer protocol + SimliAvatarAdapter skeleton
- `pyproject.toml` + `requirements.txt` with pinned Python dependencies
- `frontend/package.json` with Next.js, LiveKit, Playwright dependencies
- `frontend/lib/logger.ts` — frontend structured logger matching backend format
- `frontend/lib/types.ts` — TypeScript type contracts for cross-boundary data
- Frontend component stubs (AvatarDisplay, LatencyOverlay, SubjectSelector, etc.)
- Frontend health check API at `/api/health`
- `.env.example` with all 7 required + optional variables documented
- `.github/workflows/ci.yml` — lint + test pipeline for PRs
- `.github/workflows/integration.yml` — integration tests (manual/nightly)
- `pytest.ini`, `.coveragerc`, `playwright.config.ts` — test configuration
- `docker-compose.yml` with agent + frontend services
- `Dockerfile` for agent (Python 3.11) and frontend (Node 20) with health checks
- `scripts/lint.sh` — runs ruff + tsc + eslint
- Root `README.md` with setup, architecture, and env var documentation
- Unit tests: test_config, test_errors, test_metrics, test_avatar
