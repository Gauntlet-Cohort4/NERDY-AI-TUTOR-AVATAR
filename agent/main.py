"""Nerdy AI Tutor Agent — LiveKit AgentServer entrypoint.

This module starts the LiveKit AgentServer and wires together:
- AgentSession with STT, LLM, TTS plugins
- Simli AvatarSession for video rendering
- MetricsCollector for latency tracking
- SubjectRouterAgent as the initial agent

Implementation: Phase 2
"""
