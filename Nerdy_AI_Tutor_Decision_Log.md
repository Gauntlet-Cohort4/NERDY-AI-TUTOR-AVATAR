# Nerdy Live AI Video Tutor — Decision Log

**Choices, Rationale, and Tradeoffs**

Original: March 8, 2026 | Updated: March 9, 2026

This document records every major technical decision, why it was made, and what was traded off.

> Red **■ UPDATED** markers indicate research-driven amendments from March 9, 2026. ~~Struck-through text~~ shows original content that has been superseded. Green-bordered text shows the update.

---

## Decision 1: Architecture Approach

**Choice:** Composable Pipeline with LiveKit Agents

**Alternatives considered:** Collapsed Pipeline (OpenAI Realtime API + Avatar), Full Self-Hosted Open Source

**Why we chose this:**

The evaluation rubric requires per-stage latency breakdown (automatic -10 point deduction without it). The Collapsed Pipeline (OpenAI Realtime API) is a black box that merges STT+LLM+TTS into a single service — you cannot measure individual stage latency. The Self-Hosted approach requires 2-3 weeks and GPU provisioning, which exceeds our timeline.

The Composable Pipeline with LiveKit Agents gives us full per-stage measurement AND uses a framework that has native plugins for all our chosen services. LiveKit handles the hard parts (WebRTC, VAD, turn detection, interruptions) while we focus on service selection and prompt engineering.

| What we gain | What we give up |
|---|---|
| Full per-stage latency measurement | Simplicity of a single API call (Collapsed) |
| Ability to swap any component independently | Potentially lower latency from OpenAI native speech-to-speech |
| Clear demonstration of technical understanding | Fewer moving parts |
| Achievable in <1 week with LiveKit abstractions | Maximum optimization surface of self-hosted |

> *Research note: OpenAI Realtime API showed median turn latency of 2.24 seconds in extended testing, with degradation over time — problematic for a 1-5 minute demo. Our composable approach avoids this risk.*

### ■ UPDATED — March 9, 2026: LiveKit Agents v1.4.x API Pattern

Research finding: LiveKit Agents released v1.0 in April 2025, replacing `VoicePipelineAgent` with `Agent` + `AgentSession`. The framework is now at v1.4.4 (March 3, 2026). This strengthens the original decision:

- `AgentSession` IS the pipeline orchestrator — handles STT→LLM→TTS streaming internally. No custom orchestrator needed.
- `AgentSession` emits granular metrics events at actual pipeline boundaries, providing more accurate per-stage latency than manual timestamping.
- Agent handoff pattern enables seamless topic switching: session stays running while Agent swaps. Avatar stays connected, WebRTC does not hiccup.
- Simli attaches as `AvatarSession` wrapping the `AgentSession`, not a pipeline stage.

**Net effect:** less custom code, lower risk, same per-stage measurement capability. Note: Groq's own LiveKit docs still show the deprecated `VoicePipelineAgent` — do not follow those examples.

---

## Decision 2: Speech-to-Text — Deepgram Nova-3

**Choice:** Deepgram Nova-3 (streaming)

**Alternatives considered:** OpenAI Whisper (API/self-hosted), Google Speech-to-Text, AssemblyAI Universal-2

**Why we chose this:**

Deepgram Nova-3 is purpose-built for real-time streaming transcription with sub-300ms latency. Whisper was designed for batch transcription — it processes audio in 30-second chunks and lacks native streaming. Forcing Whisper into real-time requires custom chunking pipelines that add seconds of latency.

Deepgram also offers keyword boosting, which lets us improve recognition accuracy on academic vocabulary (photosynthesis, denominator, etc.) without building custom preprocessing.

### ■ UPDATED — March 9, 2026: Keyterm Prompting replaces Keyword Boosting

Nova-3 does NOT support the old `keywords` parameter (keyword boosting). It uses `keyterm` parameter instead, called "Keyterm Prompting." Different parameter name, different API behavior, no intensifiers. Deepgram docs state: "Keywords is only available for Nova-2, Nova-1, Enhanced, and Base. For Nova-3, use Keyterm Prompting."

Multi-word phrases are natively supported, which is an improvement. Subject-specific term lists remain identical — only the mechanism changes.

| What we gain | What we give up |
|---|---|
| Native streaming: 200-400ms latency | Whisper's slightly better accuracy on unusual accents |
| Keyterm prompting for academic terms | Open-source flexibility of self-hosted Whisper |
| Native LiveKit plugin (one line of code) | Google's 100+ language coverage |
| $200 free credit, cheapest per-minute pricing | AssemblyAI's highest streaming WER scores |

> *Mitigation for accent/noise concerns: WebRTC provides browser-side noise suppression and echo cancellation. Silero VAD ensures only actual speech reaches Deepgram. Keyterm prompting improves recognition on domain terms. For a controlled demo environment with a single English speaker, these mitigations are sufficient.*

---

## Decision 3: LLM — Groq + Llama-3.3-70B-Versatile

**Choice:** Groq running Llama-3.3-70B-Versatile

**Alternatives considered:** Groq + Llama 8B, OpenAI GPT-4o-mini, Together AI, self-hosted vLLM/llama.cpp

**Why we chose this:**

Groq's LPU hardware delivers sub-300ms time-to-first-token with deterministic latency — no unpredictable spikes. The Llama-3.3-70B-Versatile model provides strong instruction-following needed to maintain Socratic method consistently (never give direct answers, always ask guiding questions). Smaller 8B models were tested and found to break character more frequently, falling back to lecturing. GPT-4o-mini has better reasoning but 300-600ms TTFT pushes our latency budget.

| What we gain | What we give up |
|---|---|
| Sub-300ms TTFT with consistent performance | GPT-4o-mini's superior reasoning on edge cases |
| 70B model follows Socratic system prompt reliably | Speed of 8B model (~100ms faster TTFT) |
| OpenAI-compatible API (easy to swap later) | OpenAI ecosystem features (function calling polish) |
| Very low per-token cost | Vendor diversification (single inference provider) |

> *The 70B vs 8B decision is driven by the rubric: Educational Quality is 25% of the score. An 8B model that saves 100ms on TTFT but breaks Socratic method 20% of the time would cost far more in rubric points than the latency difference gains.*

### ■ UPDATED — March 9, 2026: Model Configurability + Deprecation Risk

`llama-3.3-70b-versatile` is confirmed active and is the default model in the Groq LiveKit plugin. However, Groq deprecates models aggressively — they decommissioned `llama-3.1-70b-versatile` with only two weeks' notice. The model ID is now configurable via `GROQ_MODEL` environment variable so a deprecation can be handled by changing one line in `.env`, not a code deploy. A `llama-3.3-70b-specdec` variant with speculative decoding exists as a documented future enhancement that may improve TTFT.

---

## Decision 4: Text-to-Speech — Cartesia Sonic

~~**Choice:** Cartesia Sonic~~

### ■ UPDATED

**Choice:** Cartesia Sonic-3 (model ID: `sonic-3`)

**Alternatives considered:** ElevenLabs Flash v2.5, OpenAI TTS, Coqui/XTTS (self-hosted)

**Why we chose this:**

Cartesia Sonic achieves 40-90ms time-to-first-audio — 4-10x faster than any alternative. This is built on a fundamentally different architecture (State Space Models vs Transformers) that is purpose-designed for streaming speed. ElevenLabs Flash v2.5 achieves ~75ms at its best, but Cartesia is more consistently fast and approximately 73% cheaper.

The rubric has no "voice naturalness" metric — it scores latency, lip-sync, and conversation feel. Cartesia sounds natural enough that no evaluator would flag voice quality, while its speed advantage directly impacts the highest-weighted rubric categories.

**Configuration:** Voice: Select a warm, encouraging voice appropriate for tutoring. Speed: Slightly slower than default (tutoring pacing).

### ■ UPDATED — March 9, 2026: Specific Voice Selection

Cartesia recommends specific voice IDs for voice agent use cases. Default: **Katie** (`f786b574-daa5-4673-aa0c-cbe3e8534c02`) — warm, stable, realistic. Alternative: **Kiefer** (`228fca29-3a0a-435c-8728-5cb483251068`). Voice ID configurable via `CARTESIA_VOICE_ID` env var. Utility script `scripts/list-voices.py` available for browsing alternatives.

| What we gain | What we give up |
|---|---|
| 40-90ms TTFB — fastest TTS provider | ElevenLabs' best-in-class voice expressiveness |
| 73% lower cost than ElevenLabs | 70+ language support (Cartesia supports 15) |
| Massive latency headroom for other stages | ElevenLabs' professional voice cloning quality |
| Native LiveKit plugin | Longer max text per request (500 char vs 40K) |

> *Cartesia is the single biggest latency advantage in our stack. Every millisecond saved on TTS is a millisecond the LLM can spend generating a better Socratic question.*

---

## Decision 5: Avatar — Simli Trinity

**Choice:** Simli Trinity avatars

**Alternatives considered:** HeyGen LiveAvatar, D-ID, Synthesia, SadTalker/Wav2Lip (open-source)

**Why we chose this:**

Simli is the only avatar provider with a native LiveKit Agents plugin, sub-300ms rendering latency, and a design specifically built for real-time conversational interaction. Integration requires a few lines of code and minutes of setup. HeyGen LiveAvatar offers richer expressiveness (gestures, hand movements) but at higher cost (2-4x), undocumented latency, and significantly more complex integration that would consume 1-2 additional development days.

| What we gain | What we give up |
|---|---|
| Sub-300ms rendering, well-documented | HeyGen's richer gestures and expressions |
| Native LiveKit plugin (minutes to integrate) | 1-2 potential rubric points on Video Integration |
| $0.05/min (vs $0.10-0.20/min HeyGen) | Audio-driven dynamic hand movements |
| 1-2 dev days saved for other rubric categories | "Excellent" tier avatar expressiveness (14-15 pts) |

> *The rubric math: HeyGen might gain 1-2 points on Video Integration (15% weight = 1.5-3 total points). But losing 1-2 dev days could hurt Latency (25%), Educational Quality (25%), and Documentation (10%) — worth 60% of the total score. The expected value clearly favors Simli.*

### ■ UPDATED — March 9, 2026: Plugin Risk Mitigation + Session Config

**Risk found:** The standalone `livekit-plugins-simli` PyPI package shows v1.2.6 (August 2025) while core framework is at v1.4.4. However, the plugin is maintained in the monorepo and the 1.4.3 release includes "Update Simli integration endpoint." Install via `pip install "livekit-agents[simli]"` not standalone. A known GitHub issue exists about LLM not responding on second connections with Simli.

**Mitigation:** 2-hour spike in Phase 0 to validate plugin. Wrap Simli behind `AvatarRenderer` protocol from day one — if the plugin works, great; if not, swap to Simli's direct WebRTC API with zero changes to the rest of the pipeline.

**Session config:** Set `maxSessionLength=3600` (1 hour) for production posture. Keep `maxIdleTime=300` (5 min). The default 30-min limit exists for GPU billing reasons; extending to 1 hour has no technical negative. Topic switches happen via Agent handoff within the same session — no teardown needed.

---

## Decision 6: Frontend — Custom Next.js with Latency Overlay

**Choice:** Minimal custom Next.js frontend with real-time latency metrics overlay

**Alternatives considered:** LiveKit Agents Playground (pre-built UI)

While the Playground would be fastest, a custom frontend with a live latency overlay directly supports the Latency Performance rubric category (25% weight). Showing per-stage timing on screen during the demo makes latency performance immediately visible to evaluators. The custom frontend is minimal — avatar video, latency overlay, start/stop controls — not a polished product UI.

| What we gain | What we give up |
|---|---|
| Live latency metrics visible during demo | ~4 hours of development time |
| Professional presentation | Simplicity of zero-frontend-code approach |
| Shows technical depth to evaluators | Risk of frontend bugs |

No changes from original decision.

---

## Decision 7: Subject Matter — Three Concepts Across Grades

**Choice:** Photosynthesis (7th grade), Fractions (6th grade), Newton's Third Law (9th grade)

Each concept was chosen because it has a well-known student misconception that is perfectly suited for Socratic redirection. Together they demonstrate range across subjects (biology, math, physics) and grade levels (6th through 9th). All three are universally understood by evaluators, making accuracy easy to verify. None require visual diagrams, which our avatar cannot produce.

For the demo, we plan to cover 2 of the 3 concepts in a 3-4 minute recording. The third concept provides a backup if one doesn't demonstrate the Socratic method as clearly during recording.

### ■ UPDATED — March 9, 2026: Agent Handoff for Topic Switching

Each subject is now implemented as a separate `Agent` subclass (`BiologyTutorAgent`, `MathTutorAgent`, `PhysicsTutorAgent`) with a `SubjectRouterAgent` handling initial greeting and subject selection. When the student picks a topic, the router hands off to the subject-specific agent via LiveKit's Agent handoff pattern. The `AgentSession` (the "classroom") stays running while the `Agent` (the "teacher") swaps. The avatar stays connected, WebRTC does not reconnect, and the transition is seamless. This also enables mid-session topic switching if the student asks to change subjects.

---

## Decision 8: Latency vs. Quality Tradeoff Lines

**Choice:** Voice-first modality. Speed for encouragement, quality for scaffolding.

Quick responses (encouragement, simple follow-ups) target <500ms — hitting the "Excellent" latency tier. Substantive Socratic questions (redirecting a wrong answer, building a concept) allow up to 800ms — this feels like a tutor pausing to think, which is natural and acceptable per the rubric. These tradeoffs emerge naturally from response length rather than requiring explicit routing logic.

No changes from original decision.

---

## New Decisions Added March 9, 2026

The following decisions were not in the original log but emerged from research validation.

---

## Decision 9: Async Conversation Summarization (NEW)

**Context:** The implementation plan specifies: "After 10 turns, summarize earlier exchanges into 2-3 sentences and prepend." The question was whether to build this for the demo given that a 3-4 minute demo may only reach 8-12 turns.

**Decision:** Build it. This is a production demo, not a throwback. Even if summarization barely triggers during the recording, it demonstrates production maturity to evaluators.

**Implementation:** After turn 10, fire an async background Groq call to summarize turns 1-5 into 2-3 sentences. The summary is available by turn 12-13. No latency hit to any individual turn because it runs as a background `asyncio.Task`.

| What we gain | What we give up |
|---|---|
| Production-ready conversation management | ~4 hours of development time |
| Demonstrates context management to evaluators | Slightly more complex history module |
| Enables longer sessions without context degradation | One additional Groq API call per 10 turns |

---

## Decision 10: Deepgram Flux — Documented Enhancement Only (NEW)

**Context:** Deepgram released Flux, a conversational speech recognition model that combines STT and end-of-turn detection into a single model, potentially replacing Nova-3 + Silero VAD + LiveKit turn detector.

**Decision:** Do not use for this build. Flux merges the STT and turn detection stages, making it impossible to report separate latency numbers for those components. The rubric requires per-stage latency breakdown with an automatic -10 point deduction without it. This is the same "black box" problem that eliminated the OpenAI Realtime API in Decision 1. Document as a future enhancement for scenarios where per-stage reporting matters less than conversation feel.

---

## Decision 11: Environment Variable Management (NEW)

**Decision:** All secrets and configurable values live in environment variables.

- **`.env.example`** — Checked into git. Every variable with comments explaining what it does, where to get the key, and what the default is.
- **`.env`** — Gitignored. Developer copies `.env.example` and fills in secrets.
- **`src/config.py`** fails fast on missing required variables with a clear error message listing what's missing.
- All model IDs, voice IDs, and face IDs configurable via env vars — no code changes needed for provider updates or deprecations.

> *Groq deprecates models aggressively (decommissioned llama-3.1-70b with two weeks' notice). Making model IDs env vars means a deprecation is a config change, not a code deploy.*

---

## Summary: Decision Impact on Rubric

| Decision | Primary Rubric Impact | Points | Confidence |
|---|---|---|---|
| Composable Pipeline + v1.4.x | Latency (25%) + Implementation (10%) | 35 pts | High (improved) |
| Deepgram Nova-3 + Keyterms | Latency (25%) | 25 pts | High |
| Groq + Llama 70B (env-configurable) | Latency (25%) + Educational (25%) | 50 pts | High |
| Cartesia Sonic-3 + Katie voice | Latency (25%) | 25 pts | High |
| Simli Trinity + adapter pattern | Video Integration (15%) | 15 pts | Good (11-13) |
| Custom Frontend | Latency (25%) + Innovation (15%) | 40 pts | Medium-High |
| 3 Concepts + Agent Handoff | Educational Quality (25%) | 25 pts | High (improved) |
| Speed/Quality Lines | Latency (25%) + UX | 25 pts | High |
| Async Summarization (NEW) | Implementation (10%) | 10 pts | High |
| Flux Exclusion (NEW) | Latency (25%) — protects score | N/A | High |
| Env Var Management (NEW) | Implementation (10%) | 10 pts | High |

**Overall Projected Score: 83-98 out of 100** (+ up to 8 bonus points)

The research-driven amendments do not change the projected score range. They reduce implementation risk (fewer surprises with APIs) and strengthen Implementation Quality and Documentation by demonstrating awareness of current technology state. The Agent handoff pattern is a net improvement to Educational Quality, enabling smoother demo flow.

Our strongest categories remain Educational Quality and Latency Performance (both 25% weight), where our technology choices directly optimize for the highest-scoring tiers. Our most constrained category is Video Integration (15% weight), where Simli's expressiveness gap caps us at the "Good" tier. This is an intentional, documented tradeoff — the development time saved is reinvested into categories worth 4x more of the total score.
