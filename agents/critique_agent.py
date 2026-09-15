"""Critique node: a single-pass Gemini review of the drafted report."""
import re

from langchain_google_genai import ChatGoogleGenerativeAI

import config
from state import Critique, MARSState

HEADERS = ["Strengths", "Weaknesses", "Missing Angles", "Citation Quality"]


def _build_prompt(query: str, report: str) -> str:
    # Built with an f-string (not str.format on a template) so literal { } characters
    # in the query or report body can never be misparsed as format fields.
    return (
        "You are a skeptical peer reviewer evaluating a research report.\n\n"
        f"Original research question: {query}\n\n"
        f"Report to review:\n{report}\n\n"
        "Write your review using EXACTLY these four markdown headers, each followed by "
        "a short paragraph or bullet list. Use plain text and markdown only — do not use "
        'LaTeX or math notation (write "300-500 Wh/kg", not a dollar-sign math expression).\n\n'
        "### Strengths\n### Weaknesses\n### Missing Angles\n### Citation Quality\n"
    )


def _parse_critique(raw: str) -> Critique:
    sections = {}
    pattern = r"###\s*(" + "|".join(re.escape(h) for h in HEADERS) + r")\s*\n(.*?)(?=###|\Z)"
    for match in re.finditer(pattern, raw, re.DOTALL):
        sections[match.group(1)] = match.group(2).strip()

    return Critique(
        strengths=sections.get("Strengths", ""),
        weaknesses=sections.get("Weaknesses", ""),
        missing_angles=sections.get("Missing Angles", ""),
        citation_quality=sections.get("Citation Quality", ""),
        raw_markdown=raw,
    )


def run_critique(state: MARSState) -> dict:
    try:
        llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.4,
        )
        prompt = _build_prompt(state["query"], state.get("report_markdown", ""))
        response = llm.invoke(prompt)
        raw = (response.text or "").strip()
        if not raw:
            raise ValueError("empty response")
        critique = _parse_critique(raw)
        return {"critique": critique}
    except Exception as exc:
        placeholder = Critique(
            raw_markdown=f"Critique unavailable due to an API error: {exc}"
        )
        return {
            "critique": placeholder,
            "errors": state.get("errors", [])
            + [f"Critique generation failed: {exc}"],
        }
