# OPTIMIZATION.md — Pipeline Optimization Strategies

**L.U.N.A. — Learning Unbound Nerdy AI**

This document explains what we did to optimize each pipeline stage, the reasoning behind each decision, and how we validated improvements through testing.

---

## Pipeline Overview

```
Student Mic → WebRTC/LiveKit → Deepgram STT → Groq LLM → Cartesia TTS → Avatar → WebRTC → Student Screen
```

All stages stream concurrently. Tokens stream into TTS which streams audio into the avatar renderer. The target is <500ms to first avatar frame and <1s maximum end-to-end.

---

## 1. Avatar Rendering — Provider Testing & Selection

### What we did

We tested three avatar frameworks end-to-end, measuring both startup time and in-session rendering quality:

1. **Simli Trinity** — Started here for its documented speed advantage and native LiveKit plugin.
2. **Hedra Live Avatars** — Tested as a middle ground between speed and realism.
3. **Beyond Presence** — Selected as the production provider for avatar realism.

### Why we switched

Simli produced the fastest in-session rendering, but the avatars looked noticeably less realistic — closer to animated characters than human faces. Since avatar startup time (the time from session start to first rendered frame) was **comparable across all three providers** (~8-15 seconds, dominated by LiveKit connection setup and avatar model initialization), there was no meaningful startup advantage to Simli.

The reasoning: if the user is going to wait a similar amount of time regardless, they should get the highest-quality avatar. Beyond Presence produces photorealistic faces that students are more likely to engage with as a "real tutor," which directly supports the Socratic teaching method.

### How we validated

- Measured startup time across 10+ sessions per provider
- Compared avatar visual quality through screen recordings
- Tested lip-sync accuracy with varying speech speeds
- All three providers remain available via `AVATAR_PROVIDER` env var for A/B testing

---

## 2. Text-to-Speech — Cartesia Tuning

### What we did

We tuned Cartesia Sonic-3's output to sound more natural for a tutoring context:

```python
tts = cartesia.TTS(
    model="sonic-3",
    voice=config.cartesia_voice_id,
    speed=0.95,            # Slightly slower for natural tutoring pace
    word_timestamps=False,  # Disabled to prevent last-word clipping
)
```

### Speed adjustment (`speed=0.95`)

The default speed of 1.0 produced speech that felt slightly rushed for a tutoring context. We reduced to 0.95 (range is 0.6-2.0) which:
- Sounds more like a thoughtful tutor pausing between concepts
- Adds ~50ms of tail room per utterance, giving the last audio packet time to transit WebRTC before the "done" signal closes the track
- Prevents the last word from being clipped during playback

### Word timestamps disabled

With `word_timestamps=True`, the `SentenceTokenizer` sets `flush_on_chunk=True` with `max_buffer_delay_ms=0`, causing Cartesia to flush immediately. The "done" signal then arrives before the final audio chunk finishes playing, clipping the last word. Disabling timestamps eliminated this issue entirely.

### Voice selection

We tested multiple Cartesia voices and selected one that balances warmth, clarity, and stability for extended tutoring conversations. The voice ID is configurable via `CARTESIA_VOICE_ID` for easy swapping.

---

## 3. Microphone Cutoff & Turn Detection

### What we did

We tuned the VAD (Voice Activity Detection) and endpointing parameters through iterative testing with a physical microphone:

```python
vad=silero.VAD.load(
    activation_threshold=0.65,
    min_speech_duration=0.1,
),
min_endpointing_delay=1.0,
min_interruption_duration=0.8,
```

### `min_endpointing_delay=1.0` (default: 0.5s)

This is the most critical parameter. It controls how long the system waits after the student stops speaking before considering the turn "complete." The default 0.5s was far too aggressive — it frequently cut off students mid-sentence during natural pauses (e.g., thinking about how to phrase an answer to a Socratic question).

We tested values from 0.5s to 1.5s with a physical microphone:
- **0.5s**: Cut off constantly during natural speech pauses
- **0.75s**: Still too aggressive for thoughtful responses
- **1.0s**: Sweet spot — long enough for thinking pauses, short enough to feel responsive
- **1.5s**: Felt sluggish, noticeable delay after student finishes

### `min_interruption_duration=0.8`

Controls how long a student must speak before interrupting the agent's current response. At 0.3s (low), background noise or brief "um"s would interrupt the tutor. At 0.8s, only intentional speech triggers an interruption.

### `activation_threshold=0.65`

Silero VAD's sensitivity threshold. Higher values require louder/clearer speech. 0.65 balances sensitivity (catches soft-spoken students) with noise rejection (ignores keyboard clicks, HVAC).

### How we validated

Iterative testing with a real microphone in a home office environment. Tested across:
- Speaking softly vs. loudly
- Fast speech vs. long thinking pauses
- Background noise (typing, fan)
- Intentional vs. accidental interruptions

---

## 4. Text and Audio Synchronization

### What we did

LiveKit's `AgentSession` handles the core text-to-audio synchronization out of the box — it streams LLM tokens into TTS and plays audio through the WebRTC track. However, we added a supplementary synchronization layer to handle edge cases where the Beyond Presence `TranscriptSynchronizer` could desync, truncating the on-screen transcript.

### The problem

Beyond Presence's transcript display could sometimes lag behind or truncate the agent's response text, particularly at session startup or during network hiccups. The student would hear the full response but see a cut-off transcript on screen.

### Our solution

We implemented a two-layer transcript sync:

1. **Primary: LiveKit `useTranscriptions()` hook** — Streams agent text to the frontend in real-time as tokens arrive. This handles 95%+ of cases.

2. **Fallback: `transcript_complete` data channel** — After the agent finishes a response, it publishes the complete response text on a reliable data channel topic. The frontend compares this against the streamed transcript and patches it if the published text is longer (indicating truncation occurred).

```python
# agent/main.py — publishes complete text as fallback
await room.local_participant.publish_data(
    json.dumps({"text": complete_response}),
    reliable=True,
    topic="transcript_complete",
)
```

This ensures that text always appears complete on screen regardless of streaming hiccups, and that the text starts displaying when audio starts playing — not when an internal LiveKit signal fires.

---

## 5. LLM Response Quality

### What we did

Optimized the Socratic system prompts through iterative testing to keep responses concise and pedagogically effective:

- **2-sentence response rule**: LLM responses are constrained to 2 sentences maximum for quick turns, keeping TTS generation fast
- **No-direct-answers policy**: System prompt strictly enforces Socratic questioning
- **Subject-specific keyterms**: Deepgram keyterm prompting improves STT accuracy on domain vocabulary, which in turn improves LLM response quality (garbage in → garbage out)

### Model configurability

The LLM is swappable at runtime. We tested Groq Llama 3.3 70B (fast, good Socratic compliance) and Anthropic Haiku (similar speed, better tool calling). The choice is a deployment decision, not a code change.

---

## 6. Per-Stage Latency Measurement

### What we did

The `MetricsCollector` (in `agent/src/metrics.py`) hooks into `AgentSession.metrics_collected` events and extracts per-stage timing:

| Metric | Source | What it measures |
|---|---|---|
| `stt_ms` | `EOUMetrics.transcription_delay` | Time from end-of-speech to transcript ready |
| `llm_ttft_ms` | `LLMMetrics.ttft` | Time from prompt sent to first token received |
| `tts_ttfb_ms` | `TTSMetrics.ttfb` | Time from text sent to first audio byte |
| `total_e2e_ms` | Sum of above | Full pipeline latency |

These are published to the frontend via LiveKit's data channel on the `"metrics"` topic, where the `LatencyOverlay` component displays them in real-time. Session summary stats include mean, median, P95, max, and percentage of turns under 500ms and 1000ms.

---

## 7. Infrastructure Optimization

### Docker multi-stage builds

Agent and frontend Dockerfiles use multi-stage builds to minimize image size. Build dependencies (gcc, node_modules) are discarded in the final runtime image.

### Artifact caching

Generated PDFs are cached in the database (`content_pdf` column on the `artifacts` table). First request generates the PDF; subsequent requests serve the cached bytes directly. Flash cards, worksheets, and summaries follow the same pattern — generate once via LLM, store in PostgreSQL, serve from cache.

### Concurrent streaming

All pipeline stages stream concurrently. LLM tokens stream into TTS as they arrive (not waiting for the full response). TTS audio streams into the avatar as chunks are generated. This overlapping execution is the single biggest optimization — it means total latency is closer to the **maximum** of individual stages rather than their **sum**.
