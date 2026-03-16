"""Interactive SVG template metadata for the whiteboard.

Each template defines:
- name: Human-readable label
- subjects: Which subjects can use this template
- params: Expected parameter schema (informational, validated on the frontend)
"""

from __future__ import annotations

TEMPLATES: dict[str, dict] = {
    "number_line": {
        "name": "Number Line",
        "subjects": ["math", "intro_algebra"],
        "params": {
            "min": "number (left bound)",
            "max": "number (right bound)",
            "step": "number (tick interval, default 1)",
            "markers": "array of {value: number, label?: string, color?: string}",
            "title": "string (optional)",
        },
        "example": '{"min": 0, "max": 10, "step": 1, "markers": [{"value": 3, "label": "3/1"}, {"value": 5, "label": "5/1"}], "title": "Number Line"}',
    },
    "coordinate_plane": {
        "name": "Coordinate Plane",
        "subjects": [
            "math",
            "intro_algebra",
            "algebra_ii",
            "calculus",
            "physics",
        ],
        "params": {
            "x_min": "number (default -10)",
            "x_max": "number (default 10)",
            "y_min": "number (default -10)",
            "y_max": "number (default 10)",
            "points": "array of {x: number, y: number, label?: string, color?: string}",
            "lines": "array of {slope: number, intercept: number, label?: string, color?: string}",
            "title": "string (optional)",
        },
        "example": '{"x_min": -5, "x_max": 5, "y_min": -5, "y_max": 5, "points": [{"x": 2, "y": 3, "label": "A"}], "lines": [{"slope": 1, "intercept": 0, "label": "y=x"}], "title": "Plotting Points"}',
    },
    "fraction_bars": {
        "name": "Fraction Bars",
        "subjects": ["math"],
        "params": {
            "fractions": "array of {numerator: number, denominator: number, label?: string, color?: string}",
            "show_equivalent": "boolean (optional)",
            "title": "string (optional)",
        },
        "example": '{"fractions": [{"numerator": 1, "denominator": 2, "label": "1/2"}, {"numerator": 2, "denominator": 4, "label": "2/4"}], "show_equivalent": true, "title": "Equivalent Fractions"}',
    },
    "force_vector": {
        "name": "Force Vector",
        "subjects": ["physics"],
        "params": {
            "vectors": "array of {magnitude: number, angle: number, label: string}",
            "show_resultant": "boolean",
        },
        "example": '{"vectors": [{"magnitude": 10, "angle": 0, "label": "F1"}, {"magnitude": 5, "angle": 90, "label": "F2"}], "show_resultant": true}',
    },
    "periodic_table_section": {
        "name": "Periodic Table Section",
        "subjects": ["chemistry"],
        "params": {
            "highlighted_elements": "string[] (element symbols)",
            "group_label": "string",
        },
        "example": '{"highlighted_elements": ["H", "He", "Li"], "group_label": "First Three Elements"}',
    },
}


def get_templates_for_subject(subject: str) -> dict[str, dict]:
    """Return templates available for a given subject."""
    return {
        k: v
        for k, v in TEMPLATES.items()
        if subject in v["subjects"]
    }
