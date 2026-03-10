# Changelog — Agent Backend

## [Phase 0] - 2026-03-09

### Added
- `src/config.py` — AppConfig with from_env(), fail-fast validation, defaults
- `src/logging_setup.py` — structlog JSON logging configuration
- `src/errors.py` — PipelineStage, ErrorSeverity, PipelineError, handle_pipeline_error()
- `src/types.py` — Subject, SubjectConfig, TurnMetrics, ConversationTurn, SessionState, AvatarRenderer
- `src/metrics.py` — MetricsCollector with per-turn capture and session summary stats
- `src/avatar/renderer.py` — AvatarRenderer protocol re-export + SimliAvatarAdapter skeleton
- Unit tests for config, errors, metrics, and avatar modules
- pyproject.toml, requirements.txt, pytest.ini, .coveragerc
- Dockerfile with health check
- Stub files for agents, education, and utils modules (Phase 1+)
