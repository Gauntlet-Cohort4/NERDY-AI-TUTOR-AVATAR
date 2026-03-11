"""Subject definitions and keyterm lists for Deepgram Nova-3.

SUBJECT_CONFIGS maps each Subject enum to a SubjectConfig with:
- subject:      the Subject enum value
- grade_level:  target grade as a string
- keyterms:     domain vocabulary tuple to improve Deepgram STT accuracy
- system_prompt: Socratic teaching prompt (populated from prompts module)
"""

import structlog

from src.education.prompts import get_system_prompt
from src.types import Subject, SubjectConfig

logger = structlog.get_logger(__name__)

SUBJECT_CONFIGS: dict[Subject, SubjectConfig] = {
    Subject.BIOLOGY: SubjectConfig(
        subject=Subject.BIOLOGY,
        grade_level="7th grade",
        keyterms=(
            "photosynthesis",
            "chloroplast",
            "glucose",
            "carbon dioxide",
            "oxygen",
            "chlorophyll",
            "sunlight",
            "stomata",
            "thylakoid",
            "cellular respiration",
            "autotroph",
            "ATP",
            "Calvin cycle",
            "light reaction",
        ),
        system_prompt=get_system_prompt(Subject.BIOLOGY),
    ),
    Subject.MATH: SubjectConfig(
        subject=Subject.MATH,
        grade_level="6th grade",
        keyterms=(
            "fraction",
            "numerator",
            "denominator",
            "equivalent",
            "simplify",
            "improper fraction",
            "mixed number",
            "least common denominator",
            "greatest common factor",
            "compare fractions",
            "multiply fractions",
            "divide fractions",
            "reciprocal",
        ),
        system_prompt=get_system_prompt(Subject.MATH),
    ),
    Subject.PHYSICS: SubjectConfig(
        subject=Subject.PHYSICS,
        grade_level="9th grade",
        keyterms=(
            "Newton",
            "force",
            "acceleration",
            "reaction",
            "action",
            "mass",
            "Newton's Third Law",
            "momentum",
            "velocity",
            "net force",
            "inertia",
            "friction",
            "gravity",
        ),
        system_prompt=get_system_prompt(Subject.PHYSICS),
    ),
}

logger.debug("subject_configs_loaded", subjects=list(SUBJECT_CONFIGS.keys()))


def get_keyterms(subject: Subject) -> list[str]:
    """Return keyterm list for a subject.

    Returns an empty list if the subject is not found in SUBJECT_CONFIGS.
    """
    config = SUBJECT_CONFIGS.get(subject)
    return list(config.keyterms) if config else []
