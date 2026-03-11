"""Tests for subject-specific tutor agents.

Requirement mapping:
- test_biology_agent_instantiation   → BiologyTutorAgent can be created
- test_math_agent_instantiation      → MathTutorAgent can be created
- test_physics_agent_instantiation   → PhysicsTutorAgent can be created
- test_each_uses_subject_system_prompt → agent instructions match get_system_prompt()
- test_each_is_agent_subclass        → all agents extend livekit Agent
"""

from livekit.agents import Agent

from src.types import Subject


class TestBiologyTutorAgent:
    def test_instantiation(self):
        from src.agents.biology import BiologyTutorAgent

        agent = BiologyTutorAgent()
        assert agent is not None

    def test_is_livekit_agent_subclass(self):
        from src.agents.biology import BiologyTutorAgent

        assert issubclass(BiologyTutorAgent, Agent)

    def test_is_agent_instance(self):
        from src.agents.biology import BiologyTutorAgent

        agent = BiologyTutorAgent()
        assert isinstance(agent, Agent)

    def test_has_non_empty_instructions(self):
        from src.agents.biology import BiologyTutorAgent

        agent = BiologyTutorAgent()
        instructions = getattr(agent, "_instructions", None) or getattr(agent, "instructions", None)
        assert instructions, "BiologyTutorAgent must have non-empty instructions"

    def test_instructions_match_system_prompt(self):
        from src.agents.biology import BiologyTutorAgent
        from src.education.prompts import get_system_prompt

        agent = BiologyTutorAgent()
        instructions = str(
            getattr(agent, "_instructions", "") or getattr(agent, "instructions", "")
        )
        expected = get_system_prompt(Subject.BIOLOGY)
        assert instructions == expected

    def test_instructions_contain_photosynthesis_reference(self):
        from src.agents.biology import BiologyTutorAgent

        agent = BiologyTutorAgent()
        instructions = str(
            getattr(agent, "_instructions", "") or getattr(agent, "instructions", "")
        ).lower()
        assert "photosynthesis" in instructions or "biology" in instructions


class TestMathTutorAgent:
    def test_instantiation(self):
        from src.agents.math import MathTutorAgent

        agent = MathTutorAgent()
        assert agent is not None

    def test_is_livekit_agent_subclass(self):
        from src.agents.math import MathTutorAgent

        assert issubclass(MathTutorAgent, Agent)

    def test_is_agent_instance(self):
        from src.agents.math import MathTutorAgent

        agent = MathTutorAgent()
        assert isinstance(agent, Agent)

    def test_has_non_empty_instructions(self):
        from src.agents.math import MathTutorAgent

        agent = MathTutorAgent()
        instructions = getattr(agent, "_instructions", None) or getattr(agent, "instructions", None)
        assert instructions, "MathTutorAgent must have non-empty instructions"

    def test_instructions_match_system_prompt(self):
        from src.agents.math import MathTutorAgent
        from src.education.prompts import get_system_prompt

        agent = MathTutorAgent()
        instructions = str(
            getattr(agent, "_instructions", "") or getattr(agent, "instructions", "")
        )
        expected = get_system_prompt(Subject.MATH)
        assert instructions == expected

    def test_instructions_contain_fraction_reference(self):
        from src.agents.math import MathTutorAgent

        agent = MathTutorAgent()
        instructions = str(
            getattr(agent, "_instructions", "") or getattr(agent, "instructions", "")
        ).lower()
        assert "fraction" in instructions or "math" in instructions


class TestPhysicsTutorAgent:
    def test_instantiation(self):
        from src.agents.physics import PhysicsTutorAgent

        agent = PhysicsTutorAgent()
        assert agent is not None

    def test_is_livekit_agent_subclass(self):
        from src.agents.physics import PhysicsTutorAgent

        assert issubclass(PhysicsTutorAgent, Agent)

    def test_is_agent_instance(self):
        from src.agents.physics import PhysicsTutorAgent

        agent = PhysicsTutorAgent()
        assert isinstance(agent, Agent)

    def test_has_non_empty_instructions(self):
        from src.agents.physics import PhysicsTutorAgent

        agent = PhysicsTutorAgent()
        instructions = getattr(agent, "_instructions", None) or getattr(agent, "instructions", None)
        assert instructions, "PhysicsTutorAgent must have non-empty instructions"

    def test_instructions_match_system_prompt(self):
        from src.agents.physics import PhysicsTutorAgent
        from src.education.prompts import get_system_prompt

        agent = PhysicsTutorAgent()
        instructions = str(
            getattr(agent, "_instructions", "") or getattr(agent, "instructions", "")
        )
        expected = get_system_prompt(Subject.PHYSICS)
        assert instructions == expected

    def test_instructions_contain_newton_reference(self):
        from src.agents.physics import PhysicsTutorAgent

        agent = PhysicsTutorAgent()
        instructions = str(
            getattr(agent, "_instructions", "") or getattr(agent, "instructions", "")
        ).lower()
        assert "newton" in instructions or "force" in instructions or "physics" in instructions


class TestAgentsDifferentInstructions:
    def test_biology_and_math_have_different_instructions(self):
        from src.agents.biology import BiologyTutorAgent
        from src.agents.math import MathTutorAgent

        bio = BiologyTutorAgent()
        math = MathTutorAgent()
        bio_inst = str(getattr(bio, "_instructions", "") or getattr(bio, "instructions", ""))
        math_inst = str(getattr(math, "_instructions", "") or getattr(math, "instructions", ""))
        assert bio_inst != math_inst

    def test_math_and_physics_have_different_instructions(self):
        from src.agents.math import MathTutorAgent
        from src.agents.physics import PhysicsTutorAgent

        math = MathTutorAgent()
        phys = PhysicsTutorAgent()
        math_inst = str(getattr(math, "_instructions", "") or getattr(math, "instructions", ""))
        phys_inst = str(getattr(phys, "_instructions", "") or getattr(phys, "instructions", ""))
        assert math_inst != phys_inst
