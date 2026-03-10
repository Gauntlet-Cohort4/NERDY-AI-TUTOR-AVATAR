# CLAUDE.md — Nerdy AI Tutor Avatar

Project-level instructions for Claude Code. Read this file before making any changes to this codebase.

## Project Purpose

Real-time AI video avatar tutor using Socratic teaching methods. Students speak to an animated avatar that guides them through biology, math, and physics concepts by asking questions rather than giving direct answers.

## Tech Stack

| Layer | Technology |
|---|---|
| Transport | LiveKit (WebRTC) |
| Speech-to-Text | Deepgram Nova-3 |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Text-to-Speech | Cartesia |
| Avatar rendering | Simli Trinity |
| Agent framework | `livekit-agents` (Python 3.11) |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Logging | `structlog` (backend), structured JSON (frontend) |
| Testing | pytest + coverage (backend), Playwright (frontend E2E) |
| Containers | Docker + Docker Compose |

## Pipeline

```
Student Mic → WebRTC/LiveKit → Deepgram STT → Groq LLM → Cartesia TTS → Simli Avatar → WebRTC → Student Screen
```

All stages stream concurrently. Tokens stream into TTS which streams audio into Simli. Target end-to-end latency: <500 ms first avatar frame, <1 s maximum.

## Running the Agent (Dev)

```bash
cd agent
python main.py dev
```

The agent connects to LiveKit, registers the `SubjectRouterAgent`, and waits for participants to join.

## Running the Frontend (Dev)

```bash
cd frontend
npm run dev
```

Opens at `http://localhost:3000`. Navigate to a session by selecting a subject on the home page.

## Running Tests

```bash
# Backend unit tests with coverage
cd agent
pytest tests/unit/ -v --cov=src

# Backend integration tests (requires live API keys)
cd agent
pytest tests/integration/ -v

# Frontend E2E tests
cd frontend
npx playwright test

# Lint everything (ruff + tsc + eslint)
bash scripts/lint.sh
```

Target: 80% coverage minimum. Current state: 88–92% across phases.

## File Structure

```
nerdy-ai-tutor/
├── CLAUDE.md                     # This file
├── CHANGELOG.md                  # Root changelog (all phases)
├── .env.example                  # Required env vars (copy to .env)
├── docker-compose.yml            # Full-stack deployment
├── scripts/
│   ├── lint.sh                   # Unified lint runner
│   ├── list-voices.py            # Cartesia voice listing
│   └── list-faces.py             # Simli face listing
├── agent/                        # Python — LiveKit Agent backend
│   ├── main.py                   # Entrypoint: AgentServer + pipeline wiring
│   ├── CHANGELOG.md
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   ├── src/
│   │   ├── config.py             # AppConfig with from_env(), fail-fast validation
│   │   ├── logging_setup.py      # structlog JSON configuration
│   │   ├── errors.py             # PipelineError types + Socratic fallback responses
│   │   ├── types.py              # Shared dataclasses and protocols
│   │   ├── metrics.py            # MetricsCollector (per-turn latency)
│   │   ├── agents/
│   │   │   ├── router.py         # SubjectRouterAgent — greets, routes via function_tool
│   │   │   ├── biology.py        # BiologyTutorAgent
│   │   │   ├── math.py           # MathTutorAgent
│   │   │   └── physics.py        # PhysicsTutorAgent
│   │   ├── education/
│   │   │   ├── prompts.py        # Socratic system prompts per subject
│   │   │   ├── subjects.py       # SUBJECT_CONFIGS dict + STT keyterms
│   │   │   └── history.py        # Immutable ConversationHistory
│   │   └── avatar/
│   │       └── renderer.py       # AvatarRenderer protocol + SimliAvatarAdapter
│   └── tests/
│       └── unit/                 # All unit tests (pytest)
└── frontend/                     # Next.js 14 frontend
    ├── CHANGELOG.md
    ├── Dockerfile
    ├── app/
    │   ├── page.tsx              # Home page (SubjectSelector)
    │   ├── layout.tsx
    │   ├── globals.css           # Tailwind + custom component classes
    │   ├── api/
    │   │   ├── health/           # GET /api/health
    │   │   └── token/            # GET /api/token?subject=&participantName=
    │   └── session/
    │       ├── page.tsx          # Session page (LiveKitRoom wrapper)
    │       └── SessionInner.tsx  # Hooks bridge inside LiveKitRoom context
    ├── components/
    │   ├── AvatarDisplay.tsx     # Remote video track + SVG fallback
    │   ├── LatencyOverlay.tsx    # Real-time per-stage latency display
    │   ├── SubjectSelector.tsx   # Subject picker (Biology/Math/Physics)
    │   ├── SessionControls.tsx   # Connect/disconnect controls
    │   └── ConnectionStatus.tsx  # LiveKit connection state indicator
    └── lib/
        ├── livekit.ts            # Token fetch, state mapping, metrics parsing
        ├── logger.ts             # Structured JSON logger
        └── types.ts              # TypeScript contracts
```

## Coding Conventions

### Immutability (CRITICAL)
Never mutate existing objects. Always return new instances. See `ConversationHistory.add_turn()` for the canonical pattern.

### File Size
Target 200–400 lines per file. Hard limit: 800 lines. Split into focused modules rather than growing a single file.

### Logging
Use `structlog` on the backend. Import `configure_logging()` from `src/logging_setup.py` and `get_logger()` for per-module loggers. On the frontend use `lib/logger.ts` — structured JSON, never `console.log`.

### Error Handling
All errors must be caught and wrapped in `PipelineError` with a stage, severity, and user-facing Socratic fallback message. Never swallow exceptions silently.

### Test-Driven Development
Write tests first (RED), implement to pass (GREEN), then refactor. Do not merge code with coverage below 80%.

### Secrets
Never hardcode secrets. All API keys are read from environment variables via `AppConfig.from_env()`. Required keys fail fast at startup if missing.

## Environment Variables

See `.env.example` for the full list. Required:
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- `DEEPGRAM_API_KEY`
- `GROQ_API_KEY`
- `CARTESIA_API_KEY`
- `SIMLI_API_KEY`
