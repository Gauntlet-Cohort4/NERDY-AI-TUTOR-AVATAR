# COST_ANALYSIS.md — Infrastructure Cost Analysis & Scaling Plan

**L.U.N.A. — Learning Unbound Nerdy AI**

This document analyzes the per-session cost of running L.U.N.A. and projects infrastructure costs at 100, 1,000, and 100,000 concurrent users.

---

## Assumptions

| Parameter | Value | Rationale |
|---|---|---|
| Session duration | 30 minutes | Typical tutoring session length |
| Turns per session | 80 (40 student + 40 tutor) | Active back-and-forth conversation |
| Avg student utterance | ~5 seconds of audio | Short answers to Socratic questions |
| Avg tutor response | ~50 tokens output, ~500 tokens input (with context) | 2-sentence Socratic responses |
| Avg TTS characters per response | ~150 characters | 2 sentences of spoken text |
| Sessions per user per day | 1 | Conservative estimate |

---

## Per-Service Pricing (March 2026)

### Deepgram Nova-3 (Speech-to-Text)

| Tier | Streaming Rate | Source |
|---|---|---|
| Pay-as-you-go | $0.0077/min | [deepgram.com/pricing](https://deepgram.com/pricing) |
| Growth (annual) | $0.0065/min | Volume discount ~16% |
| Enterprise | Custom | Contact sales |

**Per session (30 min):** $0.231 (pay-as-you-go)

*Note: Only student speech is transcribed (~3.3 min of actual audio in 30 min session). However, the streaming connection is open for the full session duration. Billing is based on connection time for streaming.*

### Groq — Llama 3.3 70B Versatile (LLM)

| Metric | Rate | Source |
|---|---|---|
| Input tokens | $0.59/million | [groq.com/pricing](https://groq.com/pricing) |
| Output tokens | $0.79/million | [groq.com/pricing](https://groq.com/pricing) |

**Per session (80 turns):**
- Input: 80 turns × ~500 tokens = 40,000 tokens → $0.024
- Output: 80 turns × ~50 tokens = 4,000 tokens → $0.003
- **Total: $0.027**

### Anthropic Claude Haiku 4.5 (Alternative LLM)

| Metric | Rate | Source |
|---|---|---|
| Input tokens | $1.00/million | [platform.claude.com/docs](https://platform.claude.com/docs/en/about-claude/pricing) |
| Output tokens | $5.00/million | [platform.claude.com/docs](https://platform.claude.com/docs/en/about-claude/pricing) |

**Per session (80 turns):**
- Input: 40,000 tokens → $0.040
- Output: 4,000 tokens → $0.020
- **Total: $0.060** (~2.2x more than Groq)

*Prompt caching can reduce input costs by up to 90% for repeated system prompts.*

### Cartesia Sonic-3 (Text-to-Speech)

| Tier | Rate | Source |
|---|---|---|
| Credit-based | ~1 credit/character | [cartesia.ai/pricing](https://cartesia.ai/pricing) |
| Estimated cost | ~$0.05/1,000 characters | Based on plan pricing |

**Per session (80 tutor responses):**
- 40 responses × 150 characters = 6,000 characters → **$0.30**

### Avatar Rendering

| Provider | Rate | Source |
|---|---|---|
| Simli Trinity | $0.05/min (standard), <$0.01/min (Trinity-1) | [simli.com](https://simli.com) |
| Hedra | $0.05/min | [hedra.com/pricing](https://hedra.com/pricing) |
| Beyond Presence | ~$0.05/min (estimated from plan tiers) | [beyondpresence.ai/pricing](https://beyondpresence.ai/pricing) |

**Per session (30 min):** $1.50 (at $0.05/min)

### LiveKit Cloud (WebRTC Transport)

| Metric | Rate | Source |
|---|---|---|
| Agent session minutes | $0.01/min (after included) | [livekit.com/pricing](https://livekit.com/pricing) |
| Video participant | $0.02/min | Bandwidth-dependent |
| Audio participant | $0.005/min | Lower bandwidth |

**Per session (30 min, 1 video + 1 audio participant):**
- Agent: $0.30
- Video: $0.60
- **Total: $0.90**

### Anthropic Claude Sonnet (Artifact Generation)

Used for generating summaries, cheat sheets, worksheets, and flash cards post-session.

| Metric | Rate |
|---|---|
| Input tokens | $3.00/million |
| Output tokens | $15.00/million |

**Per session (4 artifacts, ~2K input + ~1K output each):**
- Input: 8,000 tokens → $0.024
- Output: 4,000 tokens → $0.060
- **Total: $0.084**

---

## Per-Session Cost Summary

| Service | Cost (Groq) | Cost (Haiku) |
|---|---|---|
| Deepgram STT | $0.231 | $0.231 |
| LLM (conversation) | $0.027 | $0.060 |
| Cartesia TTS | $0.300 | $0.300 |
| Avatar (Beyond Presence) | $1.500 | $1.500 |
| LiveKit Cloud | $0.900 | $0.900 |
| Artifact generation | $0.084 | $0.084 |
| **Total per session** | **$3.04** | **$3.08** |

**The avatar and LiveKit transport dominate costs at ~79% of the total.** LLM costs are negligible by comparison.

---

## Scaling Projections

### 100 Daily Active Users

| Metric | Value |
|---|---|
| Sessions/day | 100 |
| Monthly sessions | 3,000 |
| Monthly cost | **$9,126** |
| Per-user/month | **$91.26** |

At this scale, free tiers cover a meaningful portion of costs (Deepgram $200 credit, LiveKit included minutes, Groq free tier). Realistic monthly cost is likely **$5,000-7,000** after free tier offsets.

### 1,000 Daily Active Users

| Metric | Value |
|---|---|
| Sessions/day | 1,000 |
| Monthly sessions | 30,000 |
| Monthly cost | **$91,260** |
| Per-user/month | **$91.26** |

At this scale, volume discounts become meaningful:
- Deepgram Growth tier: ~16% savings on STT
- LiveKit Scale plan: 50,000 included agent minutes
- Avatar provider enterprise pricing: typically 30-50% discount
- **Estimated with discounts: $55,000-70,000/month**

### 100,000 Daily Active Users

| Metric | Value |
|---|---|
| Sessions/day | 100,000 |
| Monthly sessions | 3,000,000 |
| Monthly cost (list price) | **$9,126,000** |
| Per-user/month (list) | **$91.26** |

At enterprise scale, the cost structure changes fundamentally:

| Optimization | Estimated Savings |
|---|---|
| Enterprise pricing (all APIs) | 30-50% |
| Self-hosted LiveKit (eliminates transport cost) | ~30% of total |
| Avatar provider volume deal | 40-60% |
| Prompt caching (Anthropic) | 50-90% on artifact gen |
| Groq enterprise / self-hosted LLM | 50-70% |
| **Estimated optimized** | **$2.5M-4.5M/month** |
| **Per-user/month optimized** | **$25-45** |

### Cost Reduction Strategies for Scale

1. **Self-host LiveKit** — Eliminates the $0.90/session transport cost (30% of total). LiveKit is open source; self-hosting on cloud VMs is straightforward.

2. **Self-host LLM** — At 100K users, running Llama 3.3 70B on dedicated GPU instances (e.g., 8× A100 cluster) costs ~$15K/month and handles thousands of concurrent requests — far cheaper than per-token API pricing.

3. **Avatar caching/precomputation** — Pre-render common avatar idle animations and mouth shapes locally, reducing per-minute avatar API costs.

4. **STT optimization** — Only open streaming connections during active speech (not the full session), reducing Deepgram billing from 30 min to ~5 min of actual audio.

5. **Tiered service** — Offer a text-only mode (no avatar) at dramatically lower cost (~$0.56/session) for price-sensitive deployments.

---

## Break-Even Pricing

| Scenario | Cost/session | Suggested price/session | Monthly subscription (30 sessions) |
|---|---|---|---|
| Small scale (100 users) | $3.04 | $5.00 | $30/month |
| Medium scale (1K users, discounts) | $2.00 | $3.50 | $20/month |
| Large scale (100K users, self-hosted) | $0.80-1.50 | $2.50 | $15/month |

---

## Key Takeaway

**Avatar rendering and WebRTC transport are the dominant costs**, not LLM or STT. The most impactful cost optimization at scale is self-hosting LiveKit and negotiating enterprise avatar pricing. LLM costs are a rounding error at all scales.
