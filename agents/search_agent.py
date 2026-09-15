"""Search node: runs a Tavily web search for the research query."""
from tavily import TavilyClient

import config
from state import MARSState, SearchResult


def run_search(state: MARSState) -> dict:
    query = state["query"]

    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        # "basic" depth badly mishandles natural-language "What is/are…" questions
        # (returns dictionary definitions of the word "what" instead of real results),
        # so "advanced" is used despite its higher free-tier credit cost.
        response = client.search(query=query, max_results=6, search_depth="advanced")
    except Exception as exc:
        return {
            "fatal_error": (
                f"Tavily search failed: {exc}. Check TAVILY_API_KEY / usage limits."
            )
        }

    raw_results = response.get("results", []) if isinstance(response, dict) else []
    if not raw_results:
        return {
            "fatal_error": (
                "Tavily search returned no results for this query. "
                "Try rephrasing your question."
            )
        }

    search_results = [
        SearchResult(
            title=r.get("title", "Untitled"),
            url=r.get("url", ""),
            snippet=r.get("content", ""),
            score=r.get("score", 0.0),
        )
        for r in raw_results
        if r.get("url")
    ]

    if not search_results:
        return {
            "fatal_error": (
                "Tavily search returned no usable results for this query. "
                "Try rephrasing your question."
            )
        }

    return {"search_results": search_results}
