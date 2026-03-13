"""Tests for SUBJECT_CONFIGS in education/subjects.py.

Requirement mapping:
- test_all_subjects_present        → SUBJECT_CONFIGS has all 11 subjects
- test_each_config_has_keyterms    → each SubjectConfig has non-empty keyterms tuple
- test_each_config_has_grade_level → each SubjectConfig has non-empty grade_level
- test_biology_keyterms_content    → Biology keyterms contain photosynthesis-related terms
- test_math_keyterms_content       → Math keyterms contain fraction-related terms
- test_physics_keyterms_content    → Physics keyterms contain Newton's law terms
- test_configs_are_frozen          → SubjectConfig instances are immutable (frozen dataclass)
- test_subject_enum_matches_config → config.subject matches the dict key
"""

import pytest

from src.types import Subject, SubjectConfig


class TestSubjectConfigsPresence:
    def test_all_subjects_present(self):
        from src.education.subjects import SUBJECT_CONFIGS

        for subject in Subject:
            assert subject in SUBJECT_CONFIGS, f"{subject} missing from SUBJECT_CONFIGS"

    def test_all_eleven_subjects_present(self):
        from src.education.subjects import SUBJECT_CONFIGS

        assert len(SUBJECT_CONFIGS) == 11

    def test_all_values_are_subject_config_instances(self):
        from src.education.subjects import SUBJECT_CONFIGS

        for subject, config in SUBJECT_CONFIGS.items():
            assert isinstance(config, SubjectConfig), (
                f"Expected SubjectConfig for {subject}, got {type(config)}"
            )


class TestSubjectConfigKeyterms:
    def test_each_config_has_keyterms(self):
        from src.education.subjects import SUBJECT_CONFIGS

        for subject, config in SUBJECT_CONFIGS.items():
            assert config.keyterms, f"Empty keyterms for {subject}"
            assert isinstance(config.keyterms, tuple), f"keyterms must be a tuple for {subject}"
            assert len(config.keyterms) >= 5, f"Expected at least 5 keyterms for {subject}"

    def test_biology_keyterms_content(self):
        from src.education.subjects import SUBJECT_CONFIGS

        config = SUBJECT_CONFIGS[Subject.BIOLOGY]
        keyterms_lower = [k.lower() for k in config.keyterms]
        assert any("chloroplast" in k for k in keyterms_lower)
        assert any("glucose" in k for k in keyterms_lower)
        assert any("photosynthesis" in k for k in keyterms_lower)

    def test_math_keyterms_content(self):
        from src.education.subjects import SUBJECT_CONFIGS

        config = SUBJECT_CONFIGS[Subject.MATH]
        keyterms_lower = [k.lower() for k in config.keyterms]
        assert any("numerator" in k for k in keyterms_lower)
        assert any("denominator" in k for k in keyterms_lower)
        assert any("fraction" in k for k in keyterms_lower)

    def test_physics_keyterms_content(self):
        from src.education.subjects import SUBJECT_CONFIGS

        config = SUBJECT_CONFIGS[Subject.PHYSICS]
        keyterms_lower = [k.lower() for k in config.keyterms]
        assert any("force" in k for k in keyterms_lower)
        assert any("acceleration" in k for k in keyterms_lower)


class TestSubjectConfigGradeLevel:
    def test_each_config_has_grade_level(self):
        from src.education.subjects import SUBJECT_CONFIGS

        for subject, config in SUBJECT_CONFIGS.items():
            assert config.grade_level, f"Empty grade_level for {subject}"
            assert isinstance(config.grade_level, str)

    def test_biology_is_7th_grade(self):
        from src.education.subjects import SUBJECT_CONFIGS

        config = SUBJECT_CONFIGS[Subject.BIOLOGY]
        assert "7" in config.grade_level

    def test_math_is_6th_grade(self):
        from src.education.subjects import SUBJECT_CONFIGS

        config = SUBJECT_CONFIGS[Subject.MATH]
        assert "6" in config.grade_level

    def test_physics_is_11th_grade(self):
        from src.education.subjects import SUBJECT_CONFIGS

        config = SUBJECT_CONFIGS[Subject.PHYSICS]
        assert "11" in config.grade_level


class TestSubjectConfigImmutability:
    def test_configs_are_frozen(self):
        from src.education.subjects import SUBJECT_CONFIGS

        config = SUBJECT_CONFIGS[Subject.BIOLOGY]
        with pytest.raises((AttributeError, TypeError)):
            config.grade_level = "10th grade"  # type: ignore

    def test_subject_enum_matches_config_key(self):
        from src.education.subjects import SUBJECT_CONFIGS

        for subject, config in SUBJECT_CONFIGS.items():
            assert config.subject == subject, (
                f"Config subject {config.subject} does not match key {subject}"
            )
