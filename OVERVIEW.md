# Nerdy AI Tutor Avatar — System Overview

Machine-readable codebase overview for agent consumption.

## Tech Stack

| Layer | Tech | Config |
|---|---|---|
| Transport | LiveKit (WebRTC) | LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET |
| STT | Deepgram Nova-3 (streaming websocket) | DEEPGRAM_API_KEY, DEEPGRAM_MODEL |
| LLM | Groq llama-3.3-70b-versatile | GROQ_API_KEY, GROQ_MODEL |
| TTS | Cartesia sonic-3 | CARTESIA_API_KEY, CARTESIA_MODEL, CARTESIA_VOICE_ID |
| Avatar | Simli Trinity (lip-sync video) | SIMLI_API_KEY, SIMLI_FACE_ID |
| VAD | Silero (activation_threshold=0.65, min_speech_duration=0.1) | In-code config |
| Agent Framework | livekit-agents (Python 3.11) | agent/main.py entrypoint |
| Frontend | Next.js 14, TypeScript, Tailwind CSS | frontend/ directory |
| Logging | structlog JSON (backend), lib/logger.ts JSON (frontend) | LOG_LEVEL env var |
| Testing | pytest + coverage (backend), Playwright (frontend) | 80% min coverage |
| Containers | Docker + Docker Compose | docker-compose.yml |

## Pipeline

```
Student Mic → WebRTC/LiveKit → Deepgram STT → Groq LLM → Cartesia TTS → Simli Avatar → WebRTC → Student Screen
```

All stages stream concurrently. Target: <500ms first avatar frame, <1s max E2E.

## Backend Architecture (agent/)

### Entry Point: agent/main.py
- Starts LiveKit AgentServer with HTTP health server on port 8080
- Wires: STT (Deepgram) → LLM (Groq) → TTS (Cartesia) → Avatar (Simli)
- Creates AgentSession with Silero VAD
- Room name format: `tutor-{subject}-g{grade}-{timestamp}`
- `_resolve_agent(room_name)` parses room name → direct routes to subject agent
- Falls back to SubjectRouterAgent if subject not in room name
- `_parse_grade(parts)` extracts grade (6-12) from room name parts like `g7`
- `_SUBJECT_AGENTS` maps 11 subject keys to agent classes

### Config: agent/src/config.py
- AppConfig dataclass, loaded via `from_env()` with fail-fast validation
- All env vars centralized here — no `os.getenv()` elsewhere
- Required keys fail at startup if missing

### Types: agent/src/types.py
- Subject enum: BIOLOGY, MATH, EARTH_SCIENCE, INTRO_ALGEBRA, ALGEBRA_II, CHEMISTRY, CELL_BIOLOGY, WORLD_HISTORY, CALCULUS, PHYSICS, AP_BIOLOGY
- SubjectConfig: frozen dataclass (grade_level, keyterms, system_prompt)
- TurnMetrics: stt_ms, llm_ttft_ms, tts_ttfb_ms, avatar_render_ms, total_e2e_ms
- ConversationTurn: immutable (role, content, turn_number, metrics)
- AvatarRenderer protocol: start(), close()

### Metrics: agent/src/metrics.py
- MetricsCollector accumulates per-stage latencies from AgentSession events
- Publishes TurnMetrics JSON to LiveKit data channel (topic: "metrics")
- Computes aggregates: mean, median, p95, % under thresholds
- Fire-and-forget publish — never crashes pipeline

### Errors: agent/src/errors.py
- PipelineError dataclass: stage, severity, retry count
- Fallback Socratic responses for graceful recovery
- Error handler logs + returns natural-sounding messages

### Logging: agent/src/logging_setup.py
- structlog JSON config with timestamps, components, events
- `configure_logging()` called once at startup

### Agents: agent/src/agents/

**router.py — SubjectRouterAgent**
- Greets student, asks which subject
- `select_subject()` function_tool dynamically imports + instantiates subject agent
- `_SUBJECT_ROUTES` dict maps 11 subjects to (log_event, module_path, class_name, display)
- Passes `grade=self._grade` to instantiated agents

**base.py — SubjectTutorAgent**
- Base class for all subject tutors
- `_update_stt_keyterms()` configures Deepgram with subject-specific vocabulary
- `_subject` class attribute, `_grade` instance attribute

**11 Subject Agents** (biology.py, math.py, earth_science.py, intro_algebra.py, algebra_ii.py, chemistry.py, cell_biology.py, world_history.py, calculus.py, physics.py, ap_biology.py):
- Each extends SubjectTutorAgent
- `__init__(grade=None)` → gets system prompt via `get_system_prompt(subject, grade=grade)`
- `on_enter()` → calls `_update_stt_keyterms()` + `session.generate_reply()` with subject-specific greeting

### Education: agent/src/education/

**prompts.py**
- `_PROMPTS` dict: per-subject Socratic system prompts
- Grade-aware adaptation: `_apply_grade(prompt, grade)` rewrites grade references
- `_grade_language_clause(grade)`: middle school (6-8) / high school (9-10) / advanced (11-12)
- `_boundary_clause(subject)`: off-topic redirect guardrail
- Rules: never give direct answers, ask leading questions, 2-sentence max, celebrate reasoning

**subjects.py**
- `SUBJECT_CONFIGS` dict: 11 SubjectConfig entries
- Each has: grade_level, keyterms tuple (for Deepgram STT boost), reference to prompt

**history.py**
- ConversationHistory: immutable rolling window with token budgeting
- `add_turn()` returns new instance (never mutates)
- `summarize()` triggers async LLM summarization of old turns
- `to_chat_context()` prepends summary + recent turns

**tracker.py**
- ConversationTracker: listens to `conversation_item_added` events
- Triggers summarization at turn threshold

### Avatar: agent/src/avatar/renderer.py
- SimliAvatarAdapter wraps livekit.plugins.simli.AvatarSession
- Implements AvatarRenderer protocol
- Lip-sync driven by TTS audio output
- Graceful degradation if Simli unavailable

## Frontend Architecture (frontend/)

### Pages

**app/page.tsx — Home / Subject Selector**
- Grade picker (6-12) with age-band grouping
- Subject grid filtered by grade appropriateness
- Navigates to `/session?subject={subject}&grade={grade}`

**app/session/page.tsx — Session Container**
- Parses URL params: subject, grade (validated 6-12)
- Fetches LiveKit token from `/api/token?subject=...&grade=...`
- Wraps SessionInner in `<LiveKitRoom>` with Suspense boundary
- Layout: main area (avatar video) + right sidebar (transcript)
- Controls: mic toggle, metrics toggle, transcript toggle, end session

**app/session/SessionInner.tsx — Hook Bridge**
- Runs inside LiveKitRoom context (required for LiveKit hooks)
- useConnectionState → maps to app connection state
- useDataChannel("metrics") → parses and forwards TurnMetrics
- useTranscriptions → consolidates user STT segments into single bubble per utterance
  - processedCountRef tracks cumulative index to avoid re-processing
  - userUtteranceId ref advances only when agent responds (role switch)
- Renders nothing — purely a hook bridge

### API Routes

**app/api/token/route.ts**
- Validates subject against VALID_SUBJECTS set
- Parses grade (6-12)
- Generates LiveKit JWT via AccessToken SDK
- Room name: `tutor-{subject}-g{grade}-{timestamp}`
- Returns: { token, url, subject, room, identity, healthy }

**app/api/health/route.ts**
- GET → { status: "ok", service, timestamp }

### Components

**AvatarDisplay.tsx** — Remote video track rendering with animated loading particles + crossfade reveal
**LatencyOverlay.tsx** — Fixed bottom-left overlay: per-stage current vs. average latencies, turn count, LIVE indicator
**SessionControls.tsx** — Mic toggle, start/end session, metrics/transcript visibility toggles
**ConnectionStatus.tsx** — Colored dot + label for connection state
**TranscriptSidebar.tsx** — Right sidebar with auto-scrolling chat bubbles (user=blue, agent=green), timestamps, message count

### Utilities

**lib/livekit.ts**
- `getToken(subject, grade?)` — fetches JWT from /api/token
- `mapConnectionState()` — LiveKit internal → app state
- `computeMetricsAverages()` — immutable aggregation
- `parseMetricsMessage()` — validates data channel JSON

**lib/logger.ts** — createLogger() factory, JSON output (debug/info/warn/error)

**lib/types.ts** — Subject union, TurnMetrics, SessionSummary, MetricsAverages, ConnectionState

## Deployment

### docker-compose.yml
- Network: tutor-net bridge
- Agent service: port 8080, healthcheck /health, hot-reload volumes
- Frontend service: port 3000, healthcheck /api/health, depends on agent healthy

### Agent Dockerfile (multi-stage)
- python:3.11-slim → install requirements → copy src + main.py → expose 8080

### Frontend Dockerfile (multi-stage)
- node:20-slim → install deps → build Next.js → standalone mode → expose 3000

## Data Flows

### Session Creation
1. User picks grade + subject on home page
2. Frontend fetches token: GET /api/token?subject=biology&grade=7
3. Token API generates room name `tutor-biology-g7-{timestamp}`, returns JWT
4. LiveKitRoom connects (audio=true, video=false)
5. Agent entrypoint resolves room name → BiologyTutorAgent(grade=7)
6. Agent on_enter() greets with Socratic opener

### Conversation Loop
1. Student speaks → WebRTC → Deepgram STT (streaming)
2. STT text + conversation history → Groq LLM (Socratic system prompt)
3. LLM response → Cartesia TTS → audio stream
4. Simli avatar lip-syncs to audio → WebRTC video → student screen
5. MetricsCollector publishes turn latencies to data channel
6. Frontend LatencyOverlay renders current + average metrics
7. SessionInner consolidates transcriptions → TranscriptSidebar updates

### Metrics Flow
1. AgentSession emits stage events (STT done, LLM TTFT, TTS TTFB)
2. MetricsCollector assembles full TurnMetrics on TTS completion
3. JSON published to LiveKit data channel topic "metrics"
4. Frontend parseMetricsMessage() validates → onMetricsUpdate callback
5. LatencyOverlay renders with computeMetricsAverages()

### Conversation Summarization
1. ConversationTracker counts turns via conversation_item_added events
2. At threshold → async LLM summarization of older turns
3. ConversationHistory.summarize() returns new instance with summary prefix
4. Keeps context within token budget while preserving gist

## Key Patterns
- **Immutability**: ConversationHistory.add_turn() returns new instance; computeMetricsAverages() returns new object; all TypeScript arrays use readonly
- **Fail-fast**: AppConfig.from_env() raises on missing required env vars
- **Graceful degradation**: Avatar optional, metrics fire-and-forget, Socratic fallback responses on errors
- **Structured logging**: All backend uses structlog JSON; all frontend uses lib/logger.ts JSON
- **2-sentence response limit**: System prompts enforce concise Socratic responses

## File Index

```
agent/main.py                          # Entrypoint, AgentServer, pipeline wiring, agent resolution
agent/src/config.py                    # AppConfig with from_env() fail-fast validation
agent/src/types.py                     # Subject enum, dataclasses, protocols
agent/src/metrics.py                   # MetricsCollector, data channel publishing
agent/src/errors.py                    # PipelineError, fallback responses
agent/src/logging_setup.py             # structlog JSON configuration
agent/src/agents/router.py             # SubjectRouterAgent, select_subject tool, routing map
agent/src/agents/base.py               # SubjectTutorAgent base class
agent/src/agents/biology.py            # BiologyTutorAgent (+ 10 similar subject agents)
agent/src/education/prompts.py         # Socratic system prompts, grade adaptation
agent/src/education/subjects.py        # SUBJECT_CONFIGS dict, keyterms
agent/src/education/history.py         # ConversationHistory (immutable, token-budgeted)
agent/src/education/tracker.py         # ConversationTracker, summarization trigger
agent/src/avatar/renderer.py           # SimliAvatarAdapter, AvatarRenderer protocol
frontend/app/page.tsx                  # Home page, grade + subject selection
frontend/app/session/page.tsx          # Session page, LiveKitRoom wrapper
frontend/app/session/SessionInner.tsx  # Hook bridge, transcription consolidation
frontend/app/api/token/route.ts        # JWT generation, room name encoding
frontend/app/api/health/route.ts       # Health check endpoint
frontend/components/AvatarDisplay.tsx  # Video rendering + loading animation
frontend/components/LatencyOverlay.tsx # Real-time metrics overlay
frontend/components/SessionControls.tsx# Mic, session, visibility controls
frontend/components/ConnectionStatus.tsx# Connection state badge
frontend/components/TranscriptSidebar.tsx# Chat transcript sidebar
frontend/lib/livekit.ts               # Token fetch, state mapping, metrics parsing
frontend/lib/logger.ts                 # Structured JSON logger
frontend/lib/types.ts                  # TypeScript type contracts
docker-compose.yml                     # Agent (8080) + Frontend (3000) services
agent/Dockerfile                       # Python 3.11 multi-stage build
frontend/Dockerfile                    # Node 20 multi-stage build
.env.example                           # All required + optional env vars
```
