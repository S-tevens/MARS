"""Report node: synthesizes a structured, citation-backed report with Gemini."""
import re

from langchain_google_genai import ChatGoogleGenerativeAI

import config
from state import MARSState, SourceCitation

def _build_prompt(query: str, excerpts: str) -> str:
    # Built with an f-string (not str.format on a template) so literal { } characters
    # that show up in scraped web content can never be misparsed as format fields.
    return (
        "You are a research analyst writing a structured briefing report.\n\n"
        f"Research question: {query}\n\n"
        "You have been given numbered source excerpts below. Write a well-organized "
        "report that:\n"
        "- Starts with a single H1 title line (# Title).\n"
        "- Includes a short introductory paragraph.\n"
        "- Has 3 to 6 H2 sections (## Section Name) that synthesize themes ACROSS "
        "sources (do not simply summarize one source per section).\n"
        "- Uses inline numeric citations like [1], [2] tied to the source numbers "
        "below, placed right after the claim they support.\n"
        '- Ends with a "## Sources" section listing each numbered source as '
        '"[n] Title — URL".\n'
        "- Is approximately 600 to 1000 words.\n"
        "- Uses ONLY the information in the excerpts below. If the excerpts don't "
        "cover some aspect of the question, say so plainly instead of inventing "
        "facts.\n\n"
        f"Source excerpts:\n{excerpts}\n"
    )


def _build_excerpts(state: MARSState) -> tuple[str, list[SourceCitation], list[str]]:
    scraped_docs = state.get("scraped_docs", [])
    errors: list[str] = []

    if scraped_docs:
        sources = state.get("sources", [])
        blocks = []
        for doc, src in zip(scraped_docs, sources):
            blocks.append(f"[{src.id}] {doc.title} ({doc.url})\n{doc.text}")
        return "\n\n".join(blocks), sources, errors

    # Fallback: no page could be scraped, use Tavily snippets instead.
    search_results = state.get("search_results", [])
    sources = [
        SourceCitation(id=i + 1, url=r.url, title=r.title)
        for i, r in enumerate(search_results)
    ]
    blocks = [
        f"[{s.id}] {r.title} ({r.url})\n{r.snippet}"
        for s, r in zip(sources, search_results)
    ]
    errors.append(
        "Report generated from search snippets only (full page scraping was unavailable)."
    )
    return "\n\n".join(blocks), sources, errors


def run_report(state: MARSState) -> dict:
    excerpts, sources, fallback_errors = _build_excerpts(state)

    try:
        llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.3,
        )
        prompt = _build_prompt(state["query"], excerpts)
        response = llm.invoke(prompt)
        report_markdown = (response.text or "").strip()
    except Exception as exc:
        return {"fatal_error": f"Report generation failed (Gemini API): {exc}"}

    if not report_markdown:
        return {"fatal_error": "Report generation failed (Gemini API): empty response."}

    title_match = re.search(r"^#\s+(.+)$", report_markdown, re.MULTILINE)
    report_title = title_match.group(1).strip() if title_match else state["query"]

    return {
        "report_markdown": report_markdown,
        "report_title": report_title,
        "sources": sources,
        "errors": state.get("errors", []) + fallback_errors,
    }
