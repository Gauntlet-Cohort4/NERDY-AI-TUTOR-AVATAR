"""Tests for SubjectRouterAgent in agents/router.py.

Requirement mapping:
- test_instantiation               → SubjectRouterAgent can be created
- test_has_instructions            → agent.instructions is a non-empty string
- test_instructions_mention_subjects → greeting mentions available subjects
- test_is_agent_subclass           → SubjectRouterAgent extends livekit Agent
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from livekit.agents import Agent


class TestSubjectRouterAgentInstantiation:
    def test_instantiation(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        assert agent is not None

    def test_is_livekit_agent_subclass(self):
        from src.agents.router import SubjectRouterAgent

        assert issubclass(SubjectRouterAgent, Agent)

    def test_instance_is_agent(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        assert isinstance(agent, Agent)


class TestSubjectRouterAgentInstructions:
    def test_has_instructions_attribute(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        # livekit Agent stores instructions internally; verify it was set
        assert hasattr(agent, "_instructions") or hasattr(agent, "instructions")

    def test_instructions_are_non_empty(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        # Access via private attribute since livekit Agent stores it there
        instructions = getattr(agent, "_instructions", None) or getattr(
            agent, "instructions", None
        )
        assert instructions, "Router agent must have non-empty instructions"
        assert len(str(instructions)) > 20

    def test_instructions_mention_biology(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        instructions = str(
            getattr(agent, "_instructions", "") or getattr(agent, "instructions", "")
        ).lower()
        assert "biology" in instructions

    def test_instructions_mention_math(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        instructions = str(
            getattr(agent, "_instructions", "") or getattr(agent, "instructions", "")
        ).lower()
        assert "math" in instructions

    def test_instructions_mention_physics(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        instructions = str(
            getattr(agent, "_instructions", "") or getattr(agent, "instructions", "")
        ).lower()
        assert "physics" in instructions


class TestSubjectRouterAgentTools:
    def test_has_select_biology_tool(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        # Tools registered via @function_tool are in agent._tools or passed via tools kwarg
        # Check that the class has the method defined
        assert hasattr(SubjectRouterAgent, "select_biology") or any(
            "biology" in str(t).lower()
            for t in (getattr(agent, "_tools", None) or [])
        )

    def test_has_select_math_tool(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        assert hasattr(SubjectRouterAgent, "select_math") or any(
            "math" in str(t).lower()
            for t in (getattr(agent, "_tools", None) or [])
        )

    def test_has_select_physics_tool(self):
        from src.agents.router import SubjectRouterAgent

        agent = SubjectRouterAgent()
        assert hasattr(SubjectRouterAgent, "select_physics") or any(
            "physics" in str(t).lower()
            for t in (getattr(agent, "_tools", None) or [])
        )
