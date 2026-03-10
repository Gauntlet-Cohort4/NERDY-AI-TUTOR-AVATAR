# Changelog — Agent Backend

## [Phase 2] - 2026-03-09

### Added
- `main.py` — LiveKit `AgentServer` entrypoint; wires Deepgram STT → Groq LLM → Cartesia TTS pipeline; all stages run concurrently with streaming
- `main.py` — `create_agent_session()` pure function that builds the pipeline config from `AppConfig`; designed for unit-testability without a live server
- `main.py` — `health_check()` HTTP endpoint so Docker and CI can verify the agent service is alive
- `src/avatar/renderer.py` — Full `SimliAvatarAdapter` implementation wrapping `livekit.plugins.simli`; falls back gracefully when the Simli plugin is not installed
- `tests/unit/test_main.py` — 52 new tests covering entrypoint, pipeline wiring, and health check
- `tests/unit/test_simli_adapter.py` — 69 new tests covering SimliAvatarAdapter lifecycle and graceful degradation
- 122 tests total, 88% coverage

## [Phase 1] - 2026-03-09

### Added
- `src/education/prompts.py` — Socratic system prompts for three subjects:
  - Biology (7th grade photosynthesis): enforces 2-sentence responses, never gives direct answers
  - Math (6th grade fractions): guides students with questions, not solutions
  - Physics (9th grade Newton's Third Law): Socratic dialogue, checks prior knowledge first
- `src/education/subjects.py` — `SUBJECT_CONFIGS` mapping each `Subject` enum value to a `SubjectConfig`; includes domain keyterms tuples passed to Deepgram Nova-3 for improved STT accuracy on technical vocabulary
- `src/education/history.py` — Immutable `ConversationHistory` frozen dataclass:
  - `add_turn()` returns a new `ConversationHistory` instance (never mutates)
  - `get_context_window()` respects a token budget (approximated at 4 chars/token)
  - `summarize()` async method keeps recent turns and summarises older ones via an injected `llm_callable`
  - `to_chat_context()` maps student turns → `user` role, tutor turns → `assistant` role for LLM chat APIs
- `src/agents/biology.py` — `BiologyTutorAgent(Agent)` wired to the Biology Socratic system prompt
- `src/agents/math.py` — `MathTutorAgent(Agent)` wired to the Math Socratic system prompt
- `src/agents/physics.py` — `PhysicsTutorAgent(Agent)` wired to the Physics Socratic system prompt
- `src/agents/router.py` — `SubjectRouterAgent(Agent)`:
  - Greets the student and asks which subject they need help with
  - Three `@function_tool` methods (`select_biology`, `select_math`, `select_physics`) that call `session.update_agent()` to hand off to the appropriate subject tutor
- `tests/unit/test_subjects.py` — 121 lines, validates `SUBJECT_CONFIGS` completeness and keyterm presence
- `tests/unit/test_prompts.py` — 147 lines, validates Socratic tone and no-direct-answer rules per prompt
- `tests/unit/test_history.py` — 272 lines, validates immutability, token-budget windowing, and summarise logic
- `tests/unit/test_router.py` — 109 lines, validates routing tool calls and agent handoff
- `tests/unit/test_agents.py` — 179 lines, validates per-subject agent configuration
- 77 new tests (106 total), 92% coverage

## [Phase 0] - 2026-03-09

### Added
- `src/config.py` — `AppConfig` with `from_env()`, fail-fast validation, and typed defaults
- `src/logging_setup.py` — structlog JSON logging configuration with shared processors
- `src/errors.py` — `PipelineStage`, `ErrorSeverity`, `PipelineError`, `handle_pipeline_error()`; Socratic fallback responses per stage
- `src/types.py` — `Subject`, `SubjectConfig`, `TurnMetrics`, `ConversationTurn`, `SessionState`, `AvatarRenderer` protocol
- `src/metrics.py` — `MetricsCollector` with per-turn latency capture and session summary statistics
- `src/avatar/renderer.py` — `AvatarRenderer` protocol re-export + `SimliAvatarAdapter` skeleton
- Unit tests for config, errors, metrics, and avatar modules (29 tests)
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `.coveragerc`
- `Dockerfile` with health check
- Stub files for `agents/`, `education/`, and `utils/` modules (implemented in Phase 1+)
