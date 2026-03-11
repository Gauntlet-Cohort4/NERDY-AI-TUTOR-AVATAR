# Changelog — Agent (Python Backend)

All notable changes to the agent backend will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Phase 5] - 2026-03-11

### Added
- Code cleanup and consistent formatting across all modules

### Changed
- Test fixture updated to set all env vars explicitly instead of deleting, preventing `.env` file leakage into tests

### Decisions
- Playwright E2E tests deferred to a future phase (documented in root README); unit and integration coverage deemed sufficient for launch

## [Phase 4] - 2026-03-09

### Added
- `agent/Dockerfile` — multi-stage Python 3.11 image with health check on port 8080
- Integration test suite (`tests/integration/`) covering pipeline, session, and latency scenarios
- `scripts/benchmark.py` for performance benchmarking
- `scripts/list-voices.py` — Cartesia voice listing utility
- `scripts/list-faces.py` — Simli face listing utility
- CI pipeline job `test-backend` running pytest with coverage gate

### Changed
- CI workflow split into `lint-python` and `test-backend` jobs for parallel execution

## [Phase 3] - 2026-03-09

### Added
- MetricsCollector data channel publishing wired end-to-end: agent publishes JSON on the `"metrics"` topic, frontend `SessionInner.tsx` subscribes and feeds `LatencyOverlay`

### Changed
- No agent-side code changes beyond verifying data channel integration with the new frontend

## [Phase 2] - 2026-03-09

### Added
- `main.py` — LiveKit `AgentServer` entrypoint with full STT (Deepgram) → LLM (Groq) → TTS (Cartesia) pipeline wiring; all stages run concurrently with streaming
- `create_agent_session()` pure function producing an `AgentSessionConfig` frozen dataclass for testable pipeline configuration without a live server
- `health_check()` returning a JSON status dict, served by a daemon-thread HTTP server on port 8080
- `_resolve_agent()` — direct subject routing from room name pattern `tutor-{subject}-{timestamp}`, falling back to `SubjectRouterAgent`
- `SimliAvatarAdapter.start()` full implementation wrapping `livekit.plugins.simli.AvatarSession` with graceful degradation when the plugin is unavailable
- `MetricsCollector._publish_turn_metrics()` — fire-and-forget data channel publishing via `room.local_participant.publish_data()`
- 52 new tests for entrypoint and session wiring; 69 new tests for SimliAvatarAdapter (122 total, 88% coverage)

### Decisions
- **Direct subject routing from room name** to skip the redundant router greeting when the frontend has already selected a subject. Room name convention: `tutor-{subject}-{timestamp}`.
- **Cartesia `speed` must be a float (0.6-2.0)**, not a string enum. Set to `0.9` for slightly slower, clearer speech suitable for tutoring.
- **`_strict_tool_schema = False`** set on `groq.LLM` instance post-construction because Llama models reject OpenAI-style strict tool schemas (required fields + empty properties object). The constructor does not expose this flag. Tracked for removal once the groq plugin adds the parameter.
- **`on_enter()` lifecycle hook** used for initial greeting instead of calling `generate_reply()` immediately after `session.start()`, avoiding a race condition where the session's internal activity is not yet ready.
- **Health server runs in a daemon thread** to avoid blocking the LiveKit event loop.

## [Phase 1] - 2026-03-09

### Added
- `src/agents/router.py` — `SubjectRouterAgent(Agent)` with `select_subject` function tool that calls `ctx.session.update_agent()` to hand off to subject tutors
- `src/agents/biology.py` — `BiologyTutorAgent` (photosynthesis, 7th grade)
- `src/agents/math.py` — `MathTutorAgent` (fractions, 6th grade)
- `src/agents/physics.py` — `PhysicsTutorAgent` (Newton's Third Law, 9th grade)
- `src/education/prompts.py` — Socratic system prompts per subject; persona is "Lauren"; enforces 2-sentence response rule and no-direct-answers policy
- `src/education/subjects.py` — `SUBJECT_CONFIGS` dict mapping `Subject` enum to `SubjectConfig` with domain keyterm tuples for Deepgram STT accuracy
- `src/education/history.py` — fully immutable `ConversationHistory` (frozen dataclass); `add_turn()` returns a new instance; `get_context_window()` respects token budget (4 chars/token); async `summarize()` keeps recent turns and summarises older ones via injected `llm_callable`; `to_chat_context()` maps student→user, tutor→assistant
- 77 new tests (106 total, 92% coverage)

### Decisions
- **Consolidated 3 parameterless function tools into single `select_subject(subject: str)`** to fix Groq/Llama null-args bug. Groq sends `arguments: null` for parameterless tools, which the livekit-agents framework rejects. A single tool with a required string parameter avoids this entirely.
- **Persona renamed from "Nerdy" to "Lauren"** — user-facing avatar identity is "Lauren," a friendly and enthusiastic AI tutor.
- **`on_enter()` lifecycle hook** used instead of immediate `generate_reply()` to avoid race condition with session activity initialization.

## [Phase 0] - 2026-03-09

### Added
- `src/config.py` — `AppConfig` dataclass with `from_env()` class method; fail-fast validation for 7 required env vars (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, `GROQ_API_KEY`, `CARTESIA_API_KEY`, `SIMLI_API_KEY`); all other modules receive config via dependency injection
- `src/logging_setup.py` — `setup_logging()` configuring structlog for JSON output
- `src/errors.py` — `PipelineError` dataclass with `PipelineStage` and `ErrorSeverity` enums; `FALLBACK_RESPONSES` dict of Socratic fallback messages per stage; `MAX_RETRIES` dict; `handle_pipeline_error()` central handler
- `src/types.py` — shared dataclasses and protocols: `Subject` enum, `SubjectConfig`, `TurnMetrics`, `ConversationTurn`, `SessionState`, `AvatarRenderer` protocol
- `src/metrics.py` — `MetricsCollector` accumulating per-stage latencies from `AgentSession` `metrics_collected` events; assembles `TurnMetrics` on TTS completion; `session_summary()` with mean/median/p95/max and percent-under-threshold stats
- `src/avatar/renderer.py` — `AvatarRenderer` protocol (re-exported from types) + `SimliAvatarAdapter` skeleton with `start()` and `close()` stubs
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `.coveragerc`
- 29 unit tests: `test_config`, `test_errors`, `test_metrics`, `test_avatar`

### Decisions
- **`PipelineError` is a dataclass, not an Exception subclass** — it represents structured error metadata for logging and recovery, not something to be raised and caught in the traditional sense. The `handle_pipeline_error()` function logs the error and returns a fallback response string.
- **Token estimation uses 4 chars/token** as a rough English average, sufficient for context window budgeting without requiring a tokenizer dependency.
- **All `os.getenv()` calls centralized in `config.py`** — no other module reads environment variables directly. This ensures fail-fast validation and makes testing straightforward via dependency injection.
