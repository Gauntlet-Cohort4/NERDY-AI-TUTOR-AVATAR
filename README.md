# Nerdy Live AI Video Tutor

A real-time AI video avatar tutor that uses Socratic teaching methods to help students learn biology, math, and physics through natural conversation with an animated avatar.

All five implementation phases are complete. The system is fully wired end-to-end: LiveKit WebRTC transport, Deepgram STT, Groq LLM with Socratic subject agents, Cartesia TTS, Simli avatar rendering, and a Next.js 14 frontend.

## Architecture

```
Student Mic → WebRTC/LiveKit → Deepgram STT → Groq LLM → Cartesia TTS → Simli Avatar → WebRTC → Student Screen
```

All pipeline stages stream concurrently — tokens stream into TTS which streams audio into the avatar renderer. Target end-to-end latency: <500ms (first avatar frame), <1s max acceptable.

| Pipeline Stage | Target | Max Acceptable |
|---|---|---|
| Speech-to-text (Deepgram Nova-3) | <150ms | <300ms |
| LLM time-to-first-token (Groq) | <200ms | <400ms |
| TTS first audio byte (Cartesia) | <150ms | <300ms |
| Avatar rendering (Simli Trinity) | <100ms | <200ms |
| Network + overhead (WebRTC) | <50ms | <100ms |
| **Total end-to-end** | **<500ms** | **<1000ms** |

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional, for containerized deployment)
- API accounts: [LiveKit](https://cloud.livekit.io), [Deepgram](https://console.deepgram.com), [Groq](https://console.groq.com), [Cartesia](https://cartesia.ai), [Simli](https://app.simli.com/apikey)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Gauntlet-Cohort4/NERDY-AI-TUTOR-AVATAR.git
cd NERDY-AI-TUTOR-AVATAR

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Backend setup
cd agent
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development

# Frontend setup
cd ../frontend
npm install

# Run the agent (dev mode)
cd ../agent
python main.py dev

# Run the frontend (separate terminal)
cd ../frontend
npm run dev
```

## Environment Variables

See [.env.example](.env.example) for all required and optional variables with descriptions.

| Variable | Required | Description |
|---|---|---|
| `LIVEKIT_URL` | Yes | LiveKit server WebSocket URL |
| `LIVEKIT_API_KEY` | Yes | LiveKit API key |
| `LIVEKIT_API_SECRET` | Yes | LiveKit API secret |
| `DEEPGRAM_API_KEY` | Yes | Deepgram STT API key |
| `GROQ_API_KEY` | Yes | Groq LLM API key |
| `CARTESIA_API_KEY` | Yes | Cartesia TTS API key |
| `SIMLI_API_KEY` | Yes | Simli avatar API key |
| `GROQ_MODEL` | No | LLM model (default: llama-3.3-70b-versatile) |
| `CARTESIA_VOICE_ID` | No | TTS voice (default: Katie) |
| `SIMLI_FACE_ID` | No | Avatar face ID |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

## Running Tests

```bash
# Backend unit tests
cd agent
pytest tests/unit/ -v --cov=src --cov-report=term-missing

# Backend integration tests (requires API keys)
pytest tests/integration/ -v

# Frontend E2E tests
cd frontend
npx playwright test

# Lint everything
bash scripts/lint.sh
```

## Project Structure

```
nerdy-ai-tutor/
├── agent/                    # Python — LiveKit Agent backend
│   ├── main.py               # Entrypoint: starts LiveKit AgentServer
│   ├── src/
│   │   ├── config.py         # Central config loader
│   │   ├── logging_setup.py  # Structured logging (structlog)
│   │   ├── errors.py         # Error types + Socratic fallbacks
│   │   ├── types.py          # Shared types and protocols
│   │   ├── metrics.py        # Latency metrics collector
│   │   ├── agents/           # Subject-specific tutor agents
│   │   ├── education/        # Prompts, subjects, history
│   │   └── avatar/           # Avatar renderer abstraction
│   └── tests/
├── frontend/                 # Next.js frontend
│   ├── app/                  # Pages and API routes
│   ├── components/           # React components
│   └── lib/                  # Utilities and types
├── scripts/                  # Dev utilities
└── docker-compose.yml        # Full stack deployment
```

## Docker

```bash
# Build and run the full stack
docker compose up --build

# Or build individually
docker compose build agent
docker compose build frontend
```
