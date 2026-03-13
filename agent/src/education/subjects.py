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
    # ── Middle School (6th-8th) ──────────────────────────────────────────
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
    Subject.EARTH_SCIENCE: SubjectConfig(
        subject=Subject.EARTH_SCIENCE,
        grade_level="7th grade",
        keyterms=(
            "plate tectonics",
            "earthquake",
            "volcano",
            "rock cycle",
            "weathering",
            "erosion",
            "sedimentary",
            "igneous",
            "metamorphic",
            "tectonic plates",
            "mantle",
            "crust",
            "fault line",
            "mineral",
        ),
        system_prompt=get_system_prompt(Subject.EARTH_SCIENCE),
    ),
    Subject.INTRO_ALGEBRA: SubjectConfig(
        subject=Subject.INTRO_ALGEBRA,
        grade_level="8th grade",
        keyterms=(
            "variable",
            "expression",
            "equation",
            "coefficient",
            "constant",
            "solve",
            "linear equation",
            "slope",
            "y-intercept",
            "graph",
            "inequality",
            "substitute",
            "like terms",
            "distributive property",
        ),
        system_prompt=get_system_prompt(Subject.INTRO_ALGEBRA),
    ),
    # ── High School Lower (9th-10th) ─────────────────────────────────────
    Subject.ALGEBRA_II: SubjectConfig(
        subject=Subject.ALGEBRA_II,
        grade_level="10th grade",
        keyterms=(
            "quadratic equation",
            "polynomial",
            "factoring",
            "quadratic formula",
            "parabola",
            "vertex",
            "discriminant",
            "complex number",
            "imaginary number",
            "function transformation",
            "logarithm",
            "exponential",
            "rational expression",
            "system of equations",
        ),
        system_prompt=get_system_prompt(Subject.ALGEBRA_II),
    ),
    Subject.CHEMISTRY: SubjectConfig(
        subject=Subject.CHEMISTRY,
        grade_level="10th grade",
        keyterms=(
            "periodic table",
            "element",
            "compound",
            "chemical bond",
            "covalent bond",
            "ionic bond",
            "chemical reaction",
            "balancing equations",
            "mole",
            "Avogadro",
            "states of matter",
            "acid",
            "base",
            "pH",
        ),
        system_prompt=get_system_prompt(Subject.CHEMISTRY),
    ),
    Subject.CELL_BIOLOGY: SubjectConfig(
        subject=Subject.CELL_BIOLOGY,
        grade_level="9th grade",
        keyterms=(
            "cell membrane",
            "nucleus",
            "mitochondria",
            "ribosome",
            "organelle",
            "mitosis",
            "meiosis",
            "DNA",
            "RNA",
            "prokaryotic",
            "eukaryotic",
            "cytoplasm",
            "endoplasmic reticulum",
            "cell division",
        ),
        system_prompt=get_system_prompt(Subject.CELL_BIOLOGY),
    ),
    Subject.WORLD_HISTORY: SubjectConfig(
        subject=Subject.WORLD_HISTORY,
        grade_level="10th grade",
        keyterms=(
            "civilization",
            "empire",
            "revolution",
            "monarchy",
            "democracy",
            "trade route",
            "Silk Road",
            "colonialism",
            "Renaissance",
            "Reformation",
            "Industrial Revolution",
            "feudalism",
            "ancient Rome",
            "ancient Greece",
        ),
        system_prompt=get_system_prompt(Subject.WORLD_HISTORY),
    ),
    # ── High School Upper (11th-12th) ────────────────────────────────────
    Subject.CALCULUS: SubjectConfig(
        subject=Subject.CALCULUS,
        grade_level="12th grade",
        keyterms=(
            "limit",
            "derivative",
            "integral",
            "differentiation",
            "antiderivative",
            "fundamental theorem",
            "rate of change",
            "slope of tangent",
            "chain rule",
            "product rule",
            "quotient rule",
            "continuity",
            "Riemann sum",
            "definite integral",
        ),
        system_prompt=get_system_prompt(Subject.CALCULUS),
    ),
    Subject.PHYSICS: SubjectConfig(
        subject=Subject.PHYSICS,
        grade_level="11th grade",
        keyterms=(
            "Newton's laws",
            "force",
            "acceleration",
            "momentum",
            "energy conservation",
            "work",
            "power",
            "kinematics",
            "projectile motion",
            "friction",
            "gravity",
            "torque",
            "equilibrium",
            "free body diagram",
        ),
        system_prompt=get_system_prompt(Subject.PHYSICS),
    ),
    Subject.AP_BIOLOGY: SubjectConfig(
        subject=Subject.AP_BIOLOGY,
        grade_level="12th grade",
        keyterms=(
            "gene expression",
            "transcription",
            "translation",
            "evolution",
            "natural selection",
            "cellular signaling",
            "signal transduction",
            "ecology",
            "biodiversity",
            "protein structure",
            "enzyme",
            "mutation",
            "heredity",
            "phylogenetics",
        ),
        system_prompt=get_system_prompt(Subject.AP_BIOLOGY),
    ),
}

logger.debug("subject_configs_loaded", subjects=list(SUBJECT_CONFIGS.keys()))


def get_keyterms(subject: Subject) -> list[str]:
    """Return keyterm list for a subject.

    Returns an empty list if the subject is not found in SUBJECT_CONFIGS.
    """
    config = SUBJECT_CONFIGS.get(subject)
    return list(config.keyterms) if config else []
