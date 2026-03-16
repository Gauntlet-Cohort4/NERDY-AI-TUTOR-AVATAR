# DECISIONS.md — Architectural & Design Decision Log

**L.U.N.A. — Learning Unbound Nerdy AI**

Original: March 8, 2026 | Updated: March 16, 2026

This document records every major technical decision, why it was made, and what was traded off. It serves as the canonical reference for understanding *why* the system is built the way it is.

---

## Table of Contents

1. [Architecture Approach](#decision-1-architecture-approach)
2. [Speech-to-Text — Deepgram Nova-3](#decision-2-speech-to-text--deepgram-nova-3)
3. [LLM — Groq + Llama 3.3 70B](#decision-3-llm--groq--llama-33-70b)
4. [Text-to-Speech — Cartesia Sonic-3](#decision-4-text-to-speech--cartesia-sonic-3)
5. [Avatar Provider Selection](#decision-5-avatar-provider-selection)
6. [Frontend — Custom Next.js](#decision-6-frontend--custom-nextjs)
7. [Subject Coverage & Agent Handoff](#decision-7-subject-coverage--agent-handoff)
8. [Quality-Speed Tradeoffs](#decision-8-quality-speed-tradeoffs)
9. [Async Conversation Summarization](#decision-9-async-conversation-summarization)
10. [Deepgram Flux Exclusion](#decision-10-deepgram-flux-exclusion)
11. [Environment Variable Management](#decision-11-environment-variable-management)
12. [Session Persistence & Review System](#decision-12-session-persistence--review-system)
13. [Artifact Generation (PDF, Flash Cards, Worksheets)](#decision-13-artifact-generation)

---

## Decision 1: Architecture Approach

**Choice:** Composable Pipeline with LiveKit Agents v1.4.x

**Alternatives considered:** Collapsed Pipeline (OpenAI Realtime API + Avatar), Full Self-Hosted Open Source

**Why we chose this:**

The composable pipeline gives us full per-stage latency measurement — a hard requirement for benchmarking. OpenAI's Realtime API is a black box that merges STT+LLM+TTS into a single opaque service, making it impossible to report individual stage latency. LiveKit Agents handles the hard parts (WebRTC, VAD, turn detection, interruptions) while we focus on service selection and educational prompt engineering.

LiveKit Agents v1.4.x replaced the older `VoicePipelineAgent` with `Agent` + `AgentSession`. The `AgentSession` IS the pipeline orchestrator — it handles STT→LLM→TTS streaming internally and emits granular metrics events at actual pipeline boundaries, providing more accurate per-stage latency than manual timestamping. Agent handoff enables seamless topic switching without WebRTC reconnection.

| What we gain | What we give up |
|---|---|
| Full per-stage latency measurement | Simplicity of a single API call |
| Ability to swap any component independently | Potentially lower latency from OpenAI native speech-to-speech |
| Clear demonstration of technical understanding | Fewer moving parts |
| Achievable in <1 week with LiveKit abstractions | Maximum optimization surface of self-hosted |

---

## Decision 2: Speech-to-Text — Deepgram Nova-3

**Choice:** Deepgram Nova-3 (streaming)

**Alternatives considered:** OpenAI Whisper (API/self-hosted), Google Speech-to-Text, AssemblyAI Universal-2

**Why we chose this:**

Deepgram Nova-3 is purpose-built for real-time streaming transcription with sub-300ms latency. Whisper was designed for batch transcription — it processes audio in 30-second chunks and lacks native streaming. Nova-3 uses Keyterm Prompting (not the old `keywords` parameter) to boost recognition accuracy on academic vocabulary like "photosynthesis," "denominator," and "Newton's Third Law" without custom preprocessing.

| What we gain | What we give up |
|---|---|
| Native streaming: 200-400ms latency | Whisper's slightly better accuracy on unusual accents |
| Keyterm prompting for academic terms | Open-source flexibility of self-hosted Whisper |
| Native LiveKit plugin (one line of code) | Google's 100+ language coverage |
| $200 free credit, cheapest per-minute pricing | AssemblyAI's highest streaming WER scores |

---

## Decision 3: LLM — Groq + Llama 3.3 70B

**Choice:** Groq running Llama-3.3-70B-Versatile (primary), with Anthropic Claude Haiku as tested alternative

**Alternatives considered:** Groq + Llama 8B, OpenAI GPT-4o-mini, Together AI, self-hosted vLLM

**Why we chose this:**

Groq's LPU hardware delivers sub-300ms time-to-first-token with deterministic latency. The Llama-3.3-70B-Versatile model provides strong instruction-following needed to maintain Socratic method consistently (never give direct answers, always ask guiding questions). Smaller 8B models were tested and found to break character more frequently.

**Anthropic Haiku testing:** We tested Claude Haiku 4.5 as an alternative LLM provider and found it delivered comparable speed to Groq with improved quality — particularly around tool calling reliability. Llama 3.3 70B was good at following the Socratic method but sometimes struggled with correctly formatting and interpreting tool calls. Haiku handled these consistently. The model is configurable via environment variable (`GROQ_MODEL` or switching to Anthropic provider) so the choice can be made per-deployment.

| What we gain | What we give up |
|---|---|
| Sub-300ms TTFT with consistent performance | GPT-4o-mini's superior reasoning on edge cases |
| 70B model follows Socratic system prompt reliably | Speed of 8B model (~100ms faster TTFT) |
| OpenAI-compatible API (easy to swap later) | OpenAI ecosystem features |
| Haiku alternative for better tool calling | Single-provider simplicity |

---

## Decision 4: Text-to-Speech — Cartesia Sonic-3

**Choice:** Cartesia Sonic-3

**Alternatives considered:** ElevenLabs Flash v2.5, OpenAI TTS, Coqui/XTTS (self-hosted)

**Why we chose this:**

Cartesia Sonic achieves 40-90ms time-to-first-audio — 4-10x faster than any alternative. Built on State Space Models (not Transformers), it is purpose-designed for streaming speed. ElevenLabs Flash v2.5 achieves ~75ms at best, but Cartesia is more consistently fast and approximately 73% cheaper.

Configuration: Voice selected for warmth and clarity appropriate for tutoring. Speed set to `0.95` (slightly slower than default 1.0) to sound more natural and give the last audio packet time to transit WebRTC before the "done" signal closes the track.

| What we gain | What we give up |
|---|---|
| 40-90ms TTFB — fastest TTS provider | ElevenLabs' best-in-class voice expressiveness |
| 73% lower cost than ElevenLabs | 70+ language support (Cartesia supports 15) |
| Massive latency headroom for other stages | Professional voice cloning quality |
| Native LiveKit plugin | Longer max text per request |

---

## Decision 5: Avatar Provider Selection

**Choice:** Beyond Presence (production), with Simli and Hedra tested

**Alternatives considered:** Simli Trinity, Hedra Live Avatars, HeyGen LiveAvatar, D-ID

**Why we chose this:**

We tested three avatar providers end-to-end:

| Provider | Startup Time | Realism | Latency (in-session) | Cost |
|---|---|---|---|---|
| **Simli Trinity** | ~8-12s | Low-medium (cartoon-like) | Fastest | $0.05/min |
| **Hedra** | ~10-15s | Medium | Medium | $0.05/min |
| **Beyond Presence** | ~10-15s | High (photorealistic) | Acceptable once streaming | $0.05/min (est.) |

**Simli** was the fastest to render once connected but produced noticeably less realistic avatars. Since session startup time was similar across all three providers (the LiveKit connection and avatar initialization dominate, not the rendering pipeline), we decided that if users were going to wait a similar amount of time regardless, they should get the highest-quality avatar.

**Beyond Presence** produces photorealistic avatars that are significantly more engaging for an educational context. Students are more likely to treat a realistic avatar as a real tutor, which supports the Socratic teaching method. The in-session latency is acceptable — once the avatar is rendering, the pipeline streams smoothly.

All three providers are wrapped behind an `AvatarRenderer` protocol abstraction, so switching is a single environment variable change (`AVATAR_PROVIDER=simli|hedra|beyondpresence`).

---

## Decision 6: Frontend — Custom Next.js

**Choice:** Custom Next.js 14 frontend with real-time latency overlay

**Alternatives considered:** LiveKit Agents Playground (pre-built UI)

A custom frontend with a live latency overlay directly supports latency benchmarking — showing per-stage timing (STT, LLM TTFT, TTS TTFB, Total E2E) on screen during sessions. The custom frontend also enabled building the full review system (session history, artifacts, flash cards, worksheets).

---

## Decision 7: Subject Coverage & Agent Handoff

**Choice:** 11 subjects across grade levels, with Agent handoff for topic switching

Each subject is implemented as a configuration in `SUBJECT_CONFIGS` with Socratic system prompts, STT keyterms, and grade-appropriate vocabulary. The `SubjectRouterAgent` greets the student and routes to the appropriate subject agent via LiveKit's Agent handoff pattern — the `AgentSession` stays running while the `Agent` swaps. The avatar stays connected, WebRTC does not reconnect.

---

## Decision 8: Quality-Speed Tradeoffs

### LLM Model Selection

We tested multiple LLM configurations for both speed and educational quality:

| Model | TTFT | Socratic Compliance | Tool Calling | Notes |
|---|---|---|---|---|
| **Groq Llama 3.3 70B** | ~200ms | Excellent | Inconsistent | Great at Socratic method, sometimes misformats tool calls |
| **Groq Llama 8B** | ~100ms | Poor | Poor | Breaks character frequently, falls back to lecturing |
| **Anthropic Haiku 4.5** | ~200-300ms | Excellent | Excellent | Similar speed to Groq, better tool call reliability |
| **OpenAI GPT-4o-mini** | 300-600ms | Excellent | Excellent | Best reasoning but TTFT too high for real-time |

**Decision:** Groq Llama 3.3 70B as default (fastest reliable option), with Haiku as the recommended alternative when tool calling quality matters more than minimizing TTFT by 50-100ms. The choice is a runtime configuration.

### Avatar Provider Selection

See [Decision 5](#decision-5-avatar-provider-selection) for the full comparison. The key tradeoff: Simli was the fastest renderer but least realistic. Beyond Presence was slightly slower but produced significantly higher quality. Since startup time was comparable across providers, we chose quality.

### TTS Pacing

Cartesia `speed=0.95` trades ~5% of speech speed for natural-sounding pacing. This also provides tail room for the last audio packet to transit WebRTC before the done signal, preventing word clipping.

### Response Length

Quick responses (encouragement, simple follow-ups) target <500ms end-to-end. Substantive Socratic questions (redirecting a wrong answer, building a concept) allow up to 800ms — this feels like a tutor pausing to think, which is natural. These tradeoffs emerge naturally from response length rather than explicit routing logic.

---

## Decision 9: Async Conversation Summarization

**Decision:** Build it. After turn 10, fire an async background LLM call to summarize turns 1-5 into 2-3 sentences. The summary is available by turn 12-13. No latency hit to any individual turn because it runs as a background `asyncio.Task`.

---

## Decision 10: Deepgram Flux Exclusion

**Decision:** Do not use. Flux merges STT and turn detection into a single model, making it impossible to report separate latency numbers. Documented as a future enhancement.

---

## Decision 11: Environment Variable Management

All secrets and configurable values live in environment variables. `.env.example` is checked in with documentation. `src/config.py` fails fast on missing required variables. All model IDs, voice IDs, and avatar IDs are configurable via env vars — no code changes needed for provider updates or deprecations.

---

## Decision 12: Session Persistence & Review System

**Choice:** PostgreSQL database for session persistence, with on-demand artifact generation

Sessions, transcript turns, artifacts, and flash cards are stored in PostgreSQL (via asyncpg). After a session completes, the system generates summaries, cheat sheets, and worksheets using the configured artifact LLM (Anthropic Claude Sonnet by default). These are cached in the database. PDFs are generated on-demand using fpdf2 with DejaVuSans Unicode font support and cached after first generation.

---

## Decision 13: Artifact Generation

**Choice:** fpdf2 for PDF rendering (replaced WeasyPrint)

WeasyPrint was initially chosen for HTML→PDF rendering but exhibited a known bug (`transform` AttributeError in v62.3). Replaced with fpdf2 which is lighter, has no system dependencies beyond fonts, and generates clean PDFs. DejaVuSans Unicode TTF font loaded for content containing special characters (e.g., CO₂ subscripts from LLM output).
