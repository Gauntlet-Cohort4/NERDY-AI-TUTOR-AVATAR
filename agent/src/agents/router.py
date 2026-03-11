"""SubjectRouterAgent — greets student and hands off to subject-specific agents."""

from __future__ import annotations

from typing import Annotated

import structlog
from livekit.agents import Agent, RunContext, function_tool

logger = structlog.get_logger(__name__)

_ROUTER_INSTRUCTIONS = (
    "You are Lauren, a friendly and enthusiastic AI tutor avatar. "
    "Greet the student warmly and ask which subject they would like to study today. "
    "The available subjects are: Biology (photosynthesis), Math (fractions), "
    "and Physics (Newton's Third Law). "
    "Once the student chooses a subject, call select_subject with the subject name. "
    "Keep your greeting to 2 sentences."
)


class SubjectRouterAgent(Agent):
    """Initial routing agent that greets the student and delegates to a subject tutor."""

    def __init__(self) -> None:
        super().__init__(instructions=_ROUTER_INSTRUCTIONS)
        logger.debug("router_agent_created")

    async def on_enter(self) -> None:
        """Proactively greet the student when the agent becomes active.

        Called by the livekit-agents framework once the session's internal
        activity is fully initialised, avoiding the race condition of calling
        generate_reply() immediately after session.start().
        """
        logger.info("router_greeting_triggered")
        self.session.generate_reply()

    @function_tool
    async def select_subject(
        self,
        ctx: RunContext,
        subject: Annotated[str, "The subject the student chose: 'biology', 'math', or 'physics'"],
    ) -> str:
        """Route the student to the appropriate subject tutor."""
        subject_lower = subject.strip().lower()

        if subject_lower == "biology":
            from src.agents.biology import BiologyTutorAgent

            logger.info("routing_to_biology")
            ctx.session.update_agent(BiologyTutorAgent())
            return "Switching you to our Biology tutor now!"

        if subject_lower == "math":
            from src.agents.math import MathTutorAgent

            logger.info("routing_to_math")
            ctx.session.update_agent(MathTutorAgent())
            return "Switching you to our Math tutor now!"

        if subject_lower == "physics":
            from src.agents.physics import PhysicsTutorAgent

            logger.info("routing_to_physics")
            ctx.session.update_agent(PhysicsTutorAgent())
            return "Switching you to our Physics tutor now!"

        logger.warning("unknown_subject_requested", subject=subject)
        return f"I don't have a tutor for '{subject}' yet. Please choose Biology, Math, or Physics!"
