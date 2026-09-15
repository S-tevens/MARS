"""LangGraph StateGraph wiring for the MARS research pipeline."""
from langgraph.graph import END, START, StateGraph

from agents.critique_agent import run_critique
from agents.report_agent import run_report
from agents.scrape_agent import run_scrape
from agents.search_agent import run_search
from state import MARSState


def _route_on_fatal_error(state: MARSState) -> str:
    return "end" if state.get("fatal_error") else "continue"


def build_graph():
    builder = StateGraph(MARSState)

    builder.add_node("search", run_search)
    builder.add_node("scrape", run_scrape)
    builder.add_node("report", run_report)
    builder.add_node("critique", run_critique)

    builder.add_edge(START, "search")

    builder.add_conditional_edges(
        "search", _route_on_fatal_error, {"continue": "scrape", "end": END}
    )
    builder.add_edge("scrape", "report")
    builder.add_conditional_edges(
        "report", _route_on_fatal_error, {"continue": "critique", "end": END}
    )
    builder.add_edge("critique", END)

    return builder.compile()
