"""Tests for get_system_prompt() in education/prompts.py.

Requirement mapping:
- test_returns_non_empty_for_all_subjects → each subject yields a non-empty string
- test_contains_socratic_keywords         → prompts guide rather than give answers
- test_subject_specific_content           → each prompt references its topic
- test_grade_level_in_prompt              → grade level is referenced in prompt
- test_persona_in_prompt                  → tutor persona is set
- test_response_length_constraint         → 2-sentence rule is mentioned
"""

from src.types import Subject


class TestGetSystemPromptBasics:
    def test_returns_string_for_all_subjects(self):
        from src.education.prompts import get_system_prompt

        for subject in Subject:
            result = get_system_prompt(subject)
            assert isinstance(result, str)

    def test_returns_non_empty_for_all_subjects(self):
        from src.education.prompts import get_system_prompt

        for subject in Subject:
            result = get_system_prompt(subject)
            assert len(result) > 100, f"Prompt for {subject} is too short: {len(result)} chars"

    def test_different_prompts_per_subject(self):
        from src.education.prompts import get_system_prompt

        biology_prompt = get_system_prompt(Subject.BIOLOGY)
        math_prompt = get_system_prompt(Subject.MATH)
        physics_prompt = get_system_prompt(Subject.PHYSICS)
        assert biology_prompt != math_prompt
        assert biology_prompt != physics_prompt
        assert math_prompt != physics_prompt


class TestSocraticKeywords:
    def test_biology_prompt_contains_socratic_keywords(self):
        from src.education.prompts import get_system_prompt

        prompt = get_system_prompt(Subject.BIOLOGY).lower()
        # Should ask questions or guide, not give direct answers
        socratic_terms = ["question", "think", "guide", "hint", "ask", "wonder"]
        assert any(term in prompt for term in socratic_terms), (
            "Biology prompt missing Socratic guidance terms"
        )

    def test_math_prompt_contains_socratic_keywords(self):
        from src.education.prompts import get_system_prompt

        prompt = get_system_prompt(Subject.MATH).lower()
        socratic_terms = ["question", "think", "guide", "hint", "ask", "wonder"]
        assert any(term in prompt for term in socratic_terms)

    def test_physics_prompt_contains_socratic_keywords(self):
        from src.education.prompts import get_system_prompt

        prompt = get_system_prompt(Subject.PHYSICS).lower()
        socratic_terms = ["question", "think", "guide", "hint", "ask", "wonder"]
        assert any(term in prompt for term in socratic_terms)

    def test_prompts_do_not_instruct_to_give_direct_answers(self):
        import re

        from src.education.prompts import get_system_prompt

        for subject in Subject:
            prompt = get_system_prompt(subject).lower()
            # The prompt must NOT positively instruct giving direct answers.
            # Negative phrases like "never give the answer directly" are fine.
            # We look for imperative forms without preceding "never"/"not"/"don't".
            bad_patterns = [
                r"(?<!never )(?<!not )(?<!don't )give direct answers",
                r"tell the student the answer immediately",
                r"always provide the answer",
            ]
            for pattern in bad_patterns:
                assert not re.search(pattern, prompt), (
                    f"Prompt for {subject} appears to instruct giving direct answers"
                )


class TestSubjectSpecificContent:
    def test_biology_prompt_references_photosynthesis(self):
        from src.education.prompts import get_system_prompt

        prompt = get_system_prompt(Subject.BIOLOGY).lower()
        assert "photosynthesis" in prompt or "biology" in prompt

    def test_math_prompt_references_fractions(self):
        from src.education.prompts import get_system_prompt

        prompt = get_system_prompt(Subject.MATH).lower()
        assert "fraction" in prompt or "math" in prompt

    def test_physics_prompt_references_newtons_law(self):
        from src.education.prompts import get_system_prompt

        prompt = get_system_prompt(Subject.PHYSICS).lower()
        assert "newton" in prompt or "force" in prompt or "physics" in prompt


class TestPromptStructure:
    def test_grade_level_mentioned_in_biology_prompt(self):
        from src.education.prompts import get_system_prompt

        prompt = get_system_prompt(Subject.BIOLOGY)
        assert "7" in prompt or "seventh" in prompt.lower()

    def test_grade_level_mentioned_in_math_prompt(self):
        from src.education.prompts import get_system_prompt

        prompt = get_system_prompt(Subject.MATH)
        assert "6" in prompt or "sixth" in prompt.lower()

    def test_grade_level_mentioned_in_physics_prompt(self):
        from src.education.prompts import get_system_prompt

        prompt = get_system_prompt(Subject.PHYSICS)
        assert "11" in prompt or "eleventh" in prompt.lower()

    def test_tutor_persona_present(self):
        from src.education.prompts import get_system_prompt

        for subject in Subject:
            prompt = get_system_prompt(subject).lower()
            persona_terms = ["tutor", "teacher", "nerdy", "friendly", "avatar"]
            assert any(term in prompt for term in persona_terms), (
                f"No persona terms found in {subject} prompt"
            )

    def test_response_length_rule_present(self):
        from src.education.prompts import get_system_prompt

        for subject in Subject:
            prompt = get_system_prompt(subject).lower()
            # Should mention keeping responses short
            length_terms = ["sentence", "short", "brief", "concise", "2 sentence", "two sentence"]
            assert any(term in prompt for term in length_terms), (
                f"No length constraint found in {subject} prompt"
            )
