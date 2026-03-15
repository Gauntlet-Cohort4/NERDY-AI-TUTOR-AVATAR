# L.U.N.A. — Learning Unbound Nerdy AI

A real-time AI video avatar tutor that uses Socratic teaching methods to help students learn biology, math, physics, and more through natural conversation with an animated avatar.

All five implementation phases are complete. The system is fully wired end-to-end: LiveKit WebRTC transport, Deepgram STT, Groq LLM with Socratic subject agents, Cartesia TTS, Simli avatar rendering, and a Next.js 14 frontend.

## Architecture

```
Student Mic → WebRTC/LiveKit → Deepgram STT → Groq LLM → Cartesia TTS → Simli Avatar → WebRTC → Student Screen
```

All pipeline stages stream concurrently — tokens stream into TTS which streams audio into the avatar renderer.

| Pipeline Stage | Expected | Actual |
|---|---|---|
| Speech-to-text (Deepgram Nova-3) | ~150ms | Waiting for data |
| LLM time-to-first-token (Groq) | ~200ms | Waiting for data |
| TTS first audio byte (Cartesia) | ~150ms | Waiting for data |
| Avatar rendering (Simli Trinity) | ~100ms | Waiting for data |
| Network + overhead (WebRTC) | ~50ms | Waiting for data |
| **Total end-to-end** | **~500ms** | **Waiting for data** |

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

# Frontend E2E tests (currently deferred — see note below)
# cd frontend
# npx playwright test

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

## Deferred Work

- **Playwright E2E tests.** Frontend end-to-end tests via Playwright are deferred. The test infrastructure (Playwright config, CI job) is not yet set up. Backend unit and integration tests provide current coverage.

## Known Limitations

- **Single concurrent session per agent instance.** Each agent process handles one LiveKit room at a time. Horizontal scaling requires multiple agent instances.
- **English only.** Deepgram Nova-3 STT and Cartesia TTS are configured for English. The system prompts and keyterm lists are English-only.
- **Fixed subject set.** Only Biology, Math, and Physics are available. Adding a new subject requires a new tutor agent, system prompt, and subject config entry.
- **Simli avatar session length limits.** Simli imposes per-session duration caps. Long tutoring sessions may require reconnection logic (not currently implemented).
- **Groq rate limits.** The Groq free tier enforces requests-per-minute and tokens-per-minute limits. High-frequency usage may hit throttling.
- **No persistent conversation history.** Conversation context is held in memory for the duration of a session and discarded when the session ends. There is no cross-session persistence.

## Cost Analysis

Estimated per-API costs for running the tutor. All figures are approximate and subject to change -- check each provider's pricing page for current rates.

| Service | Pricing Model | Estimated Cost | Notes |
|---|---|---|---|
| Deepgram (STT) | Per minute of audio | ~$0.0043/min (Nova-3, pay-as-you-go) | $200 free credit on signup |
| Groq (LLM) | Per token | Free tier available; paid ~$0.59/M input, $0.79/M output (Llama 3.3 70B) | Free tier has rate limits |
| Cartesia (TTS) | Per character | ~$0.85 per 1M characters (Sonic) | Usage-based after free tier |
| Simli (Avatar) | Per minute of video | Free tier: 50 min/month + $10 credit | Paid plans for higher volume |
| LiveKit (Transport) | Per participant-minute | Cloud free tier available; ~$0.004/participant-min after | Self-hosted option eliminates this cost |

A typical 10-minute tutoring session uses roughly: 10 min STT, 1-2K LLM tokens, 3-5K TTS characters, and 10 min avatar rendering. Most development and light usage fits comfortably within free tiers.
