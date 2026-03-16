# L.U.N.A. — Learning Unbound Nerdy AI

A real-time AI video avatar tutor that uses Socratic teaching methods to help students learn biology, math, physics, and more through natural conversation with an animated avatar.

All implementation phases are complete. The system is fully wired end-to-end: LiveKit WebRTC transport, Deepgram STT, Groq LLM with Socratic subject agents, Cartesia TTS, configurable avatar rendering (Beyond Presence, Simli, Hedra), a Next.js 14 frontend with session reviews, flash cards, worksheets, and PDF export.

## Architecture

```
Student Mic → WebRTC/LiveKit → Deepgram STT → Groq LLM → Cartesia TTS → Avatar → WebRTC → Student Screen
```

All pipeline stages stream concurrently — tokens stream into TTS which streams audio into the avatar renderer.

## Latency Benchmarks

**Target:** <500ms first avatar frame, <1s maximum end-to-end.

Once the avatar session is loaded, the per-stage latency measured during live tutoring sessions:

| Pipeline Stage | Target | Avg (Measured) | Current (Peak) |
|---|---|---|---|
| Speech-to-Text (Deepgram Nova-3) | <200ms | **98ms** | 197ms |
| LLM Time-to-First-Token (Groq) | <300ms | **717ms** | 510ms |
| TTS First Audio Byte (Cartesia) | <150ms | **234ms** | 257ms |
| **Total pipeline** | **<500ms** | **~1,049ms** | ~964ms |

LLM TTFT is the dominant contributor to end-to-end latency. The average exceeds target due to longer Socratic responses requiring more generation time. Current (single-turn) measurements often come in under target. STT and TTS consistently meet their individual targets.

*Note: Avatar rendering latency is handled by the avatar provider's pipeline and is not measured separately — it overlaps with audio playback via WebRTC streaming. Session startup (avatar initialization) takes 8-15 seconds across all tested providers.*

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
| `AVATAR_PROVIDER` | No | Avatar provider: `beyondpresence`, `simli`, or `hedra` (default: simli) |
| `BEY_API_KEY` | Conditional | Beyond Presence API key (required if AVATAR_PROVIDER=beyondpresence) |
| `BEY_AVATAR_ID` | Conditional | Beyond Presence avatar ID |
| `SIMLI_API_KEY` | Conditional | Simli avatar API key (required if AVATAR_PROVIDER=simli) |
| `HEDRA_API_KEY` | Conditional | Hedra API key (required if AVATAR_PROVIDER=hedra) |
| `GROQ_MODEL` | No | LLM model (default: llama-3.3-70b-versatile) |
| `CARTESIA_VOICE_ID` | No | TTS voice ID |
| `DATABASE_URL` | No | PostgreSQL connection string for session persistence |
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
├── agent/                        # Python — LiveKit Agent backend
│   ├── main.py                   # Entrypoint: AgentServer + pipeline wiring
│   ├── src/
│   │   ├── config.py             # Central config with fail-fast validation
│   │   ├── metrics.py            # Per-turn latency collector + data channel publishing
│   │   ├── agents/               # Subject-specific tutor agents + router
│   │   ├── education/            # Socratic prompts, subjects, history
│   │   ├── avatar/               # Avatar renderer protocol (Simli, Hedra, Beyond Presence)
│   │   ├── artifacts/            # PDF renderer, artifact generator
│   │   ├── api/                  # HTTP API router for sessions, artifacts, flash cards
│   │   └── db/                   # Database access layer (asyncpg)
│   └── tests/
├── frontend/                     # Next.js 14 frontend
│   ├── app/
│   │   ├── session/              # Live tutoring session page
│   │   ├── reviews/              # Session review list + detail + flash cards
│   │   ├── worksheet/            # Interactive worksheet page
│   │   └── api/                  # Token and health endpoints
│   ├── components/               # Avatar, latency overlay, whiteboard, controls
│   └── lib/                      # API client, types, logger
├── migrations/                   # PostgreSQL schema migrations
├── scripts/                      # Dev utilities
├── DECISIONS.md                  # Architectural decision log
├── OPTIMIZATION.md               # Pipeline optimization strategies
├── LIMITATIONS.md                # Known limitations & failure modes
├── COST_ANALYSIS.md              # Infrastructure cost analysis
└── docker-compose.yml            # Full stack (agent + frontend + PostgreSQL)
```

## Docker

```bash
# Build and run the full stack
docker compose up --build

# Or build individually
docker compose build agent
docker compose build frontend
```

## Documentation

| Document | Description |
|---|---|
| [DECISIONS.md](DECISIONS.md) | Architectural & design decision log with rationale and tradeoffs |
| [OPTIMIZATION.md](OPTIMIZATION.md) | Per-stage pipeline optimization strategies with reasoning |
| [LIMITATIONS.md](LIMITATIONS.md) | Known limitations, failure modes, and edge cases |
| [COST_ANALYSIS.md](COST_ANALYSIS.md) | Infrastructure cost analysis and scaling projections (100 to 100K users) |
| [CLAUDE.md](CLAUDE.md) | Project-level instructions for Claude Code |

## Known Limitations

Key limitations (see [LIMITATIONS.md](LIMITATIONS.md) for full details):

- **Session startup time.** Avatar initialization takes 8-15 seconds across all providers (LiveKit + avatar warm-up).
- **Connection recovery.** Choppy connections may drop the avatar stream; no automatic reconnection for the rendering pipeline.
- **LLM tool calling.** Llama 3.3 70B sometimes misformats tool calls; Anthropic Haiku is more reliable but costlier.
- **English only.** STT, TTS, and system prompts are English-only.
- **Single concurrent session per agent.** Horizontal scaling requires multiple agent instances.
- **No authentication.** Uses a hardcoded demo user ID; production requires an auth layer.

## Cost Analysis

Estimated cost per 30-minute session (80 turns). See [COST_ANALYSIS.md](COST_ANALYSIS.md) for full breakdown.

| Service | Cost/Session | Notes |
|---|---|---|
| Deepgram STT | $0.23 | Streaming at $0.0077/min |
| Groq LLM | $0.03 | Llama 3.3 70B ($0.59/$0.79 per M tokens) |
| Cartesia TTS | $0.30 | ~6K characters per session |
| Avatar (Beyond Presence) | $1.50 | $0.05/min |
| LiveKit Cloud | $0.90 | Agent + video participant |
| Artifact generation | $0.08 | Claude Sonnet for summaries/worksheets |
| **Total** | **~$3.04** | Avatar + transport = 79% of cost |

**Scaling:** At 1,000 daily users with volume discounts: ~$55-70K/month. At 100,000 users with self-hosted LiveKit + enterprise pricing: ~$25-45/user/month. See [COST_ANALYSIS.md](COST_ANALYSIS.md) for details.
