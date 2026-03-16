"""On-demand PDF rendering for artifacts (worksheets, cheat sheets, summaries).

Uses fpdf2 to generate PDF bytes. The rendered PDF is cached in the
database (content_pdf column) so subsequent requests are served directly.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from fpdf import FPDF

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Custom PDF class with header/footer and helpers
# ---------------------------------------------------------------------------

def _load_unicode_font(pdf: FPDF) -> bool:
    """Register DejaVuSans (Unicode TTF) on this PDF instance. Returns True if loaded."""
    import os
    font_dir = "/usr/share/fonts/truetype/dejavu"
    regular = os.path.join(font_dir, "DejaVuSans.ttf")
    bold = os.path.join(font_dir, "DejaVuSans-Bold.ttf")
    italic = os.path.join(font_dir, "DejaVuSans-Oblique.ttf")
    if not os.path.exists(regular):
        return False
    pdf.add_font("DejaVu", "", regular, uni=True)
    if os.path.exists(bold):
        pdf.add_font("DejaVu", "B", bold, uni=True)
    # Use regular as italic fallback if oblique variant not available
    italic_path = italic if os.path.exists(italic) else regular
    pdf.add_font("DejaVu", "I", italic_path, uni=True)
    return True


class _TutorPDF(FPDF):
    """PDF with branded header and page numbers."""

    title_text: str = ""
    _font_name: str = "Helvetica"

    def _init_fonts(self) -> None:
        """Try to load Unicode font, fall back to Helvetica."""
        if _load_unicode_font(self):
            self._font_name = "DejaVu"

    def header(self) -> None:
        self.set_font(self._font_name, "B", 10)
        self.set_text_color(10, 29, 55)
        self.cell(0, 8, "LUNA Tutor", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 122, 255)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font(self._font_name, "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    # Convenience helpers ─────────────────────────────────────────────

    def section_title(self, text: str) -> None:
        self.set_font(self._font_name, "B", 14)
        self.set_text_color(10, 29, 55)
        self.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_heading(self, text: str, r: int = 0, g: int = 122, b: int = 255) -> None:
        self.set_font(self._font_name, "B", 11)
        self.set_text_color(r, g, b)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def _reset_x(self) -> None:
        """Ensure X is at left margin before multi_cell calls."""
        self.set_x(self.l_margin)

    def body_text(self, text: str) -> None:
        self.set_font(self._font_name, "", 10)
        self.set_text_color(40, 40, 40)
        self._reset_x()
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text: str, marker: str = "-") -> None:
        self.set_font(self._font_name, "", 10)
        self.set_text_color(40, 40, 40)
        self._reset_x()
        self.multi_cell(0, 5.5, f"  {marker}  {text}")
        self.ln(1)

    def numbered_item(self, num: int, text: str) -> None:
        self.set_font(self._font_name, "", 10)
        self.set_text_color(40, 40, 40)
        self._reset_x()
        self.multi_cell(0, 5.5, f"  {num}. {text}")
        self.ln(1)

    def term_definition(self, term: str, definition: str, example: str | None = None) -> None:
        self.set_font(self._font_name, "B", 10)
        self.set_text_color(10, 29, 55)
        self._reset_x()
        self.multi_cell(0, 6, term)
        self.set_font(self._font_name, "", 10)
        self.set_text_color(60, 60, 60)
        self._reset_x()
        self.multi_cell(0, 5.5, definition)
        if example:
            self.set_font(self._font_name, "I", 9)
            self.set_text_color(120, 120, 120)
            self._reset_x()
            self.multi_cell(0, 5, f"Example: {example}")
        self.ln(2)

    def separator(self) -> None:
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)


# ---------------------------------------------------------------------------
# Renderers per artifact type
# ---------------------------------------------------------------------------

def _strip_markdown(text: str) -> str:
    """Rough strip of markdown formatting for PDF text."""
    import re
    text = re.sub(r"^#{1,4}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^- ", "- ", text, flags=re.MULTILINE)
    return text.strip()


def _render_summary(pdf: _TutorPDF, content: dict[str, Any]) -> None:
    text = content.get("text", "")
    pdf.section_title("Session Summary")
    # Split by markdown headings and render sections
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            pdf.ln(2)
        elif stripped.startswith("### "):
            pdf.sub_heading(stripped[4:])
        elif stripped.startswith("## "):
            pdf.section_title(stripped[3:])
        elif stripped.startswith("- **") and ":**" in stripped:
            # Bold label: description pattern
            parts = stripped[2:].split(":**", 1)
            label = parts[0].strip("* ")
            desc = parts[1].strip() if len(parts) > 1 else ""
            pdf.set_font(pdf._font_name, "", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 5.5, f"  -  {label}: {desc}")
            pdf.ln(1)
        elif stripped.startswith("- "):
            pdf.bullet(_strip_markdown(stripped[2:]))
        else:
            pdf.body_text(_strip_markdown(stripped))


def _render_cheat_sheet(pdf: _TutorPDF, content: dict[str, Any]) -> None:
    title = content.get("title", "Cheat Sheet")
    pdf.section_title(title)

    # Key Concepts
    concepts = content.get("key_concepts", [])
    if concepts:
        pdf.sub_heading("Key Concepts", 0, 100, 200)
        for c in concepts:
            pdf.term_definition(
                c.get("term", ""),
                c.get("definition", ""),
                c.get("example"),
            )
        pdf.separator()

    # Formulas
    formulas = content.get("formulas", [])
    if formulas:
        pdf.sub_heading("Formulas", 0, 160, 80)
        for f in formulas:
            pdf.set_font(pdf._font_name, "B", 10)
            pdf.set_text_color(10, 29, 55)
            pdf._reset_x()
            pdf.multi_cell(0, 6, f.get("name", ""))
            pdf.set_font(pdf._font_name, "", 10)
            pdf.set_text_color(60, 60, 60)
            pdf._reset_x()
            pdf.multi_cell(0, 6, f.get("latex", ""))
            pdf.set_font(pdf._font_name, "I", 9)
            pdf.set_text_color(120, 120, 120)
            pdf._reset_x()
            pdf.multi_cell(0, 5, f.get("when_to_use", ""))
            pdf.ln(2)
        pdf.separator()

    # Common Mistakes
    mistakes = content.get("common_mistakes", [])
    if mistakes:
        pdf.sub_heading("Common Mistakes", 200, 60, 60)
        for m in mistakes:
            pdf.bullet(m, "!")
        pdf.separator()

    # Memory Aids
    aids = content.get("memory_aids", [])
    if aids:
        pdf.sub_heading("Memory Aids", 130, 80, 200)
        for a in aids:
            pdf.bullet(a, "*")
        pdf.separator()

    # Quick Reference
    steps = content.get("quick_reference_steps", [])
    if steps:
        pdf.sub_heading("Quick Reference", 200, 160, 0)
        for s in steps:
            pdf.numbered_item(s.get("step", 0), s.get("description", ""))


def _render_worksheet(pdf: _TutorPDF, content: dict[str, Any]) -> None:
    title = content.get("title", "Practice Worksheet")
    pdf.section_title(title)

    instructions = content.get("instructions", "")
    if instructions:
        pdf.set_font(pdf._font_name, "I", 10)
        pdf.set_text_color(100, 100, 100)
        pdf._reset_x()
        pdf.multi_cell(0, 5.5, instructions)
        pdf.ln(4)

    problems = content.get("problems", [])
    for p in problems:
        num = p.get("number", "")
        question = p.get("question", "")
        difficulty = p.get("difficulty", "")

        pdf.set_font(pdf._font_name, "B", 10)
        pdf.set_text_color(10, 29, 55)
        pdf._reset_x()
        pdf.multi_cell(0, 5.5, f"Q{num}. {question}")

        if difficulty:
            pdf.set_font(pdf._font_name, "I", 8)
            pdf.set_text_color(160, 160, 160)
            pdf._reset_x()
            pdf.multi_cell(0, 5, f"[{difficulty}]")

        options = p.get("options")
        if options and isinstance(options, list):
            pdf.set_font(pdf._font_name, "", 10)
            pdf.set_text_color(60, 60, 60)
            for opt in options:
                pdf._reset_x()
                pdf.multi_cell(0, 5.5, f"    {opt}")

        pdf.ln(3)
        pdf.separator()

    # Answer key on new page
    pdf.add_page()
    pdf.section_title("Answer Key")
    for p in problems:
        num = p.get("number", "")
        answer = p.get("answer", "")
        explanation = p.get("explanation", "")

        pdf.set_font(pdf._font_name, "B", 10)
        pdf.set_text_color(0, 122, 255)
        pdf._reset_x()
        pdf.multi_cell(0, 5.5, f"Q{num}. {answer}")

        if explanation:
            pdf.set_font(pdf._font_name, "I", 9)
            pdf.set_text_color(100, 100, 100)
            pdf._reset_x()
            pdf.multi_cell(0, 5, explanation)

        pdf.ln(2)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_artifact_pdf(artifact_type: str, content_json: dict[str, Any] | str) -> bytes:
    """Render an artifact's JSON content to PDF bytes.

    Raises ValueError if the artifact type is not supported for PDF rendering.
    """
    # asyncpg may return JSONB as a string — parse if needed
    if isinstance(content_json, str):
        content_json = json.loads(content_json)

    pdf = _TutorPDF()
    pdf._init_fonts()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    if artifact_type == "summary":
        _render_summary(pdf, content_json)
    elif artifact_type == "cheat_sheet":
        _render_cheat_sheet(pdf, content_json)
    elif artifact_type == "worksheet":
        _render_worksheet(pdf, content_json)
    else:
        raise ValueError(f"PDF rendering not supported for artifact type: {artifact_type}")

    pdf_bytes: bytes = pdf.output()
    logger.info(
        "pdf_rendered",
        artifact_type=artifact_type,
        size_bytes=len(pdf_bytes),
    )
    return pdf_bytes
