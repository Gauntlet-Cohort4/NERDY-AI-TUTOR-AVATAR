"""SubjectRouterAgent — greets student and hands off to subject-specific agents."""

from __future__ import annotations

import importlib
from typing import Annotated

import structlog
from livekit.agents import Agent, RunContext, function_tool

logger = structlog.get_logger(__name__)

_ROUTER_INSTRUCTIONS = (
    "You are Lauren, a friendly and enthusiastic AI tutor avatar. "
    "Greet the student warmly and ask which subject they would like to study today. "
    "The available subjects are: Biology (photosynthesis), Math (fractions), "
    "Earth Science (rocks & tectonics), Intro Algebra (variables & equations), "
    "Algebra II (quadratics & polynomials), Chemistry (elements & reactions), "
    "Cell Biology (cells & organelles), World History (civilizations & empires), "
    "Calculus (derivatives & integrals), Physics (classical mechanics), "
    "and AP Biology (gene expression & evolution). "
    "Once the student chooses a subject, call select_subject with the subject name. "
    "Keep your greeting to 2 sentences."
)

# Maps subject name (lowercase) → (log event, import path, class name, display name)
_SUBJECT_ROUTES: dict[str, tuple[str, str, str, str]] = {
    "biology": ("routing_to_biology", "src.agents.biology", "BiologyTutorAgent", "Biology"),
    "math": ("routing_to_math", "src.agents.math", "MathTutorAgent", "Math"),
    "earth_science": ("routing_to_earth_science", "src.agents.earth_science", "EarthScienceTutorAgent", "Earth Science"),
    "intro_algebra": ("routing_to_intro_algebra", "src.agents.intro_algebra", "IntroAlgebraTutorAgent", "Intro Algebra"),
    "algebra_ii": ("routing_to_algebra_ii", "src.agents.algebra_ii", "AlgebraIITutorAgent", "Algebra II"),
    "chemistry": ("routing_to_chemistry", "src.agents.chemistry", "ChemistryTutorAgent", "Chemistry"),
    "cell_biology": ("routing_to_cell_biology", "src.agents.cell_biology", "CellBiologyTutorAgent", "Cell Biology"),
    "world_history": ("routing_to_world_history", "src.agents.world_history", "WorldHistoryTutorAgent", "World History"),
    "calculus": ("routing_to_calculus", "src.agents.calculus", "CalculusTutorAgent", "Calculus"),
    "physics": ("routing_to_physics", "src.agents.physics", "PhysicsTutorAgent", "Physics"),
    "ap_biology": ("routing_to_ap_biology", "src.agents.ap_biology", "APBiologyTutorAgent", "AP Biology"),
}


class SubjectRouterAgent(Agent):
    """Initial routing agent that greets the student and delegates to a subject tutor."""

    def __init__(self, grade: int | None = None) -> None:
        super().__init__(instructions=_ROUTER_INSTRUCTIONS)
        self._grade = grade
        logger.debug("router_agent_created", grade=grade)

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
        subject: Annotated[
            str,
            "The subject the student chose: 'biology', 'math', 'earth_science', "
            "'intro_algebra', 'algebra_ii', 'chemistry', 'cell_biology', "
            "'world_history', 'calculus', 'physics', or 'ap_biology'",
        ],
    ) -> str:
        """Route the student to the appropriate subject tutor."""
        subject_lower = subject.strip().lower().replace(" ", "_")

        route = _SUBJECT_ROUTES.get(subject_lower)
        if route is not None:
            log_event, module_path, class_name, display = route
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            logger.info(log_event)
            ctx.session.update_agent(agent_class(grade=self._grade))
            return f"Switching you to our {display} tutor now!"

        logger.warning("unknown_subject_requested", subject=subject)
        available = ", ".join(r[3] for r in _SUBJECT_ROUTES.values())
        return f"I don't have a tutor for '{subject}' yet. Please choose from: {available}!"
