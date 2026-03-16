# LIMITATIONS.md — Known Limitations & Failure Modes

**L.U.N.A. — Learning Unbound Nerdy AI**

This document explicitly states the known limitations, failure modes, and edge cases of the system as observed during development and testing.

---

## 1. Connection Stability & Recovery

**Limitation:** The system does not gracefully handle choppy or intermittent network connections.

If a student's internet connection degrades mid-session (packet loss, high jitter), the WebRTC transport may drop. LiveKit provides automatic reconnection at the transport layer, but the application-level state (conversation history, avatar rendering state, active agent) does not have robust recovery logic. A reconnection may result in:

- The avatar freezing or restarting its rendering pipeline
- A gap in the conversation where the LLM loses context of the last few turns
- The student needing to re-establish the session manually

**Mitigation:** Conversation history is persisted to the database per-turn, so a full page refresh will recover session context. However, the real-time avatar and audio stream must restart from scratch.

---

## 2. LLM Tool Calling Reliability

**Limitation:** Different LLM models produce significantly different results with tool calls.

Our original base model, **Groq Llama 3.3 70B Versatile**, excels at following the Socratic method — it consistently asks guiding questions rather than giving direct answers. However, it is less reliable at:

- Correctly formatting function/tool call JSON (sometimes malforms the schema)
- Reading and interpreting tool call results (occasionally ignores or misparses returned data)
- Executing multi-step tool sequences (e.g., generate artifact → store → confirm)

Testing with **Anthropic Claude Haiku 4.5** showed significantly better tool calling reliability at comparable speed. The tradeoff is cost: Haiku is more expensive per token than Groq's hosted Llama models.

**Current state:** The LLM provider is configurable at runtime. Groq is the default for cost and speed; Haiku is recommended when tool calling quality is critical (e.g., artifact generation, whiteboard tools).

---

## 3. Session Startup Time

**Limitation:** Starting a new tutoring session takes 8-15 seconds before the avatar appears.

This delay is caused by:
1. LiveKit room creation and WebRTC negotiation (~2-3s)
2. Avatar model initialization at the provider (~5-10s)
3. First STT/TTS warm-up (~1-2s)

This startup time is **consistent across all tested avatar providers** (Simli, Hedra, Beyond Presence). Simli's rendering pipeline is faster once connected, but the initial connection overhead is comparable. This was a key factor in choosing Beyond Presence — since startup time was similar regardless of provider, we chose the one with the highest visual quality.

**Mitigation:** The frontend shows a loading state with connection status indicators. Once the avatar is loaded, subsequent turns have sub-second latency.

---

## 4. Avatar Realism vs. Speed Tradeoff

**Limitation:** There is no avatar provider that is both photorealistic and instant.

- **Simli Trinity**: Fastest rendering, least realistic (animated/cartoon-like appearance)
- **Hedra**: Middle ground, moderate realism
- **Beyond Presence**: Most realistic, acceptable latency once streaming

Lip-sync accuracy varies across providers and is dependent on TTS audio characteristics. None of the providers achieve perfect lip-sync for all phonemes.

---

## 5. Language Support

**Limitation:** English only.

The entire system is configured for English:
- Deepgram Nova-3 STT keyterms are English academic vocabulary
- Socratic system prompts are written in English
- Cartesia TTS voice is English
- Subject content (biology, math, physics) uses English terminology

Supporting additional languages would require per-language system prompts, keyterm lists, voice selection, and potentially different STT/TTS providers.

---

## 6. Subject Set

**Limitation:** Fixed set of 11 subjects.

Adding a new subject requires:
1. A new entry in `SUBJECT_CONFIGS` with keyterms and grade configuration
2. A Socratic system prompt tailored to the subject
3. STT keyterms for domain-specific vocabulary

The system does not dynamically generate subject expertise — it follows pre-authored prompts.

---

## 7. Single Concurrent Session Per Agent

**Limitation:** Each agent process handles one LiveKit room at a time.

Horizontal scaling requires deploying multiple agent instances. There is no built-in load balancing or session routing. LiveKit Cloud handles participant routing to rooms, but each room requires a dedicated agent process.

---

## 8. Groq Rate Limits

**Limitation:** Groq's API enforces requests-per-minute and tokens-per-minute limits.

On the free tier, sustained high-frequency usage (rapid back-and-forth conversation) can hit throttling. This manifests as increased LLM TTFT or 429 errors. Paid tiers have higher limits but are still not unlimited.

**Mitigation:** The system prompt enforces short responses (2 sentences), keeping per-turn token usage low. The `min_endpointing_delay=1.0s` naturally paces conversation to ~1 turn per 2-3 seconds, staying well within rate limits for single sessions.

---

## 9. Conversation Context Window

**Limitation:** Long sessions may degrade in quality as conversation history exceeds the context window.

The conversation history module implements async summarization (after turn 10, older turns are summarized into 2-3 sentences). However, very long sessions (50+ turns) may still lose nuanced context from early in the conversation. The summarization is lossy by design.

---

## 10. Avatar Session Duration

**Limitation:** Avatar providers impose per-session duration caps.

Simli and Beyond Presence have maximum session lengths (configurable, default 3600 seconds / 1 hour). Sessions exceeding this limit will have the avatar disconnect. There is no automatic reconnection logic for avatar timeout — the student must start a new session.

---

## 11. PDF Generation

**Limitation:** PDF rendering uses basic text layout, not rich HTML.

The fpdf2-based PDF renderer supports text, bullet points, numbered lists, and term/definition pairs, but does not render:
- LaTeX math formulas (rendered as raw LaTeX text in PDF)
- Images or diagrams
- Complex table layouts
- Markdown formatting (bold/italic stripped to plain text)

The browser-based views (session detail page) provide richer rendering with KaTeX for formulas and styled HTML via react-markdown.

---

## 12. No Authentication

**Limitation:** The system uses a hardcoded demo user ID.

There is no user authentication, registration, or multi-user session isolation. All sessions and artifacts are associated with a single demo user (`00000000-0000-0000-0000-000000000001`). Production deployment would require an authentication layer (OAuth, JWT, etc.) and per-user data isolation.

---

## 13. No Offline Support

**Limitation:** The system requires a live internet connection to all external APIs.

There is no offline mode, local model fallback, or graceful degradation if any API is unreachable. If Deepgram, Groq, Cartesia, or the avatar provider is down, the session fails. The health check endpoint (`/health`) only verifies the agent process is running, not that downstream APIs are available.
