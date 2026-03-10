"""SubjectRouterAgent — greets student and hands off to subject-specific agents."""

import structlog
from livekit.agents import Agent, AgentSession, function_tool

logger = structlog.get_logger(__name__)

_ROUTER_INSTRUCTIONS = (
    "You are Nerdy, a friendly and enthusiastic AI tutor avatar. "
    "Greet the student warmly and ask which subject they would like to study today. "
    "The available subjects are: Biology (photosynthesis), Math (fractions), "
    "and Physics (Newton's Third Law). "
    "Once the student chooses a subject, use the appropriate tool to hand them off "
    "to the right tutor. Keep your greeting to 2 sentences."
)


class SubjectRouterAgent(Agent):
    """Initial routing agent that greets the student and delegates to a subject tutor."""

    def __init__(self) -> None:
        super().__init__(instructions=_ROUTER_INSTRUCTIONS)
        logger.debug("router_agent_created")

    @function_tool
    async def select_biology(self, session: AgentSession) -> str:
        """Hand the student off to the Biology tutor for a photosynthesis lesson."""
        from src.agents.biology import BiologyTutorAgent

        logger.info("routing_to_biology")
        session.update_agent(BiologyTutorAgent())
        return "Switching you to our Biology tutor now!"

    @function_tool
    async def select_math(self, session: AgentSession) -> str:
        """Hand the student off to the Math tutor for a fractions lesson."""
        from src.agents.math import MathTutorAgent

        logger.info("routing_to_math")
        session.update_agent(MathTutorAgent())
        return "Switching you to our Math tutor now!"

    @function_tool
    async def select_physics(self, session: AgentSession) -> str:
        """Hand the student off to the Physics tutor for a Newton's Third Law lesson."""
        from src.agents.physics import PhysicsTutorAgent

        logger.info("routing_to_physics")
        session.update_agent(PhysicsTutorAgent())
        return "Switching you to our Physics tutor now!"
