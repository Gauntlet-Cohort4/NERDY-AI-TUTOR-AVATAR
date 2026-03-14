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
            "min": "number",
            "max": "number",
            "markers": "number[]",
            "labels": "string[]",
        },
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
            "points": "array",
            "lines": "array",
            "domain": "[min, max]",
            "range": "[min, max]",
        },
    },
    "fraction_bars": {
        "name": "Fraction Bars",
        "subjects": ["math"],
        "params": {
            "numerator": "number",
            "denominator": "number",
            "highlighted_parts": "number",
        },
    },
    "force_vector": {
        "name": "Force Vector",
        "subjects": ["physics"],
        "params": {
            "vectors": "array of {magnitude, angle, label}",
            "show_resultant": "boolean",
        },
    },
    "periodic_table_section": {
        "name": "Periodic Table Section",
        "subjects": ["chemistry"],
        "params": {
            "highlighted_elements": "string[]",
            "group_label": "string",
        },
    },
}


def get_templates_for_subject(subject: str) -> dict[str, dict]:
    """Return templates available for a given subject."""
    return {
        k: v
        for k, v in TEMPLATES.items()
        if subject in v["subjects"]
    }
