"""Renders the final report, critique, and sources into a downloadable PDF."""
from datetime import datetime

from fpdf import FPDF

from state import MARSState

_UNICODE_MAP = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", "•": "-",
    "⁻": "-",  # superscript minus (e.g. 10⁻³)
    "⁰": "0", "¹": "1", "²": "2", "³": "3",
    "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7",
    "⁸": "8", "⁹": "9",  # superscript digits
    "₀": "0", "₁": "1", "₂": "2", "₃": "3",
    "₄": "4", "₅": "5", "₆": "6", "₇": "7",
    "₈": "8", "₉": "9",  # subscript digits
}


def _clean(text: str) -> str:
    if not text:
        return ""
    for src, dst in _UNICODE_MAP.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


class MARSPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "MARS Research Report", align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def block(self, h, text, markdown=False, indent=0):
        """multi_cell that always resets the cursor back to the left margin."""
        if indent:
            self.set_x(self.l_margin + indent)
        self.multi_cell(0, h, text, markdown=markdown, new_x="LMARGIN", new_y="NEXT")


def _write_markdown_body(pdf: MARSPDF, markdown_text: str):
    pdf.set_text_color(0, 0, 0)
    for line in markdown_text.splitlines():
        line = _clean(line.strip())
        if not line:
            pdf.ln(3)
            continue
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 18)
            pdf.block(10, line[2:])
            pdf.ln(2)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.block(9, line[3:])
            pdf.ln(1)
        elif line.startswith("- ") or line.startswith("* "):
            pdf.set_font("Helvetica", "", 11)
            pdf.block(7, f"- {line[2:]}", markdown=True, indent=5)
        else:
            pdf.set_font("Helvetica", "", 11)
            pdf.block(7, line, markdown=True)


def generate_pdf_bytes(state: MARSState) -> bytes:
    pdf = MARSPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.block(12, _clean(state.get("report_title", "Research Report")))

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.block(6, f"Query: {_clean(state.get('query', ''))}")
    pdf.block(6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    pdf.ln(6)

    _write_markdown_body(pdf, state.get("report_markdown", ""))

    critique = state.get("critique")
    if critique is not None:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(0, 0, 0)
        pdf.block(10, "Critique")
        pdf.ln(1)

        has_sections = any(
            [critique.strengths, critique.weaknesses, critique.missing_angles, critique.citation_quality]
        )
        if has_sections:
            for label, text in [
                ("Strengths", critique.strengths),
                ("Weaknesses", critique.weaknesses),
                ("Missing Angles", critique.missing_angles),
                ("Citation Quality", critique.citation_quality),
            ]:
                pdf.set_font("Helvetica", "B", 12)
                pdf.block(8, label)
                pdf.set_font("Helvetica", "", 11)
                pdf.block(7, _clean(text) or "-")
                pdf.ln(1)
        elif critique.raw_markdown:
            pdf.set_font("Helvetica", "", 11)
            pdf.block(7, _clean(critique.raw_markdown))

    sources = state.get("sources", [])
    if sources:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(0, 0, 0)
        pdf.block(10, "Sources")
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        for src in sources:
            pdf.set_text_color(0, 0, 200)
            pdf.cell(0, 7, _clean(f"[{src.id}] {src.title}"), link=src.url, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(80, 80, 80)
            pdf.block(6, _clean(src.url))
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)

    return bytes(pdf.output())
