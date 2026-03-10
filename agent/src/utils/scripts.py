"""Voice and face listing utilities.

Shared helpers used by scripts/list-voices.py and scripts/list-faces.py.
"""

from __future__ import annotations


def format_table(headers: list[str], rows: list[list[str]], widths: list[int]) -> str:
    """Format a list of rows into a fixed-width table string."""
    lines = []
    header_line = "".join(h.ljust(w) for h, w in zip(headers, widths))
    lines.append(header_line)
    lines.append("-" * sum(widths))
    for row in rows:
        line = "".join(str(v).ljust(w) for v, w in zip(row, widths))
        lines.append(line)
    return "\n".join(lines)
