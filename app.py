"""Streamlit UI for the MARS Multi-Agent Research Assistant."""
import streamlit as st

import config
from graph import build_graph
from pdf_export import generate_pdf_bytes

st.set_page_config(page_title="MARS - Multi-Agent Research Assistant", page_icon="🔎")

missing = config.validate_settings()
if missing:
    st.error(
        "Missing required setting(s): "
        + ", ".join(missing)
        + ". Copy `.env.example` to `.env` and fill in your API keys."
    )
    st.stop()

STAGE_LABELS = {
    "search": "🔍 Searching sources (Tavily)...",
    "scrape": "📄 Scraping & cleaning pages...",
    "report": "✍️ Drafting report (Gemini)...",
    "critique": "🧐 Critiquing draft (Gemini)...",
}

st.title("🔎 MARS")
st.caption("Multi-Agent Research Assistant — search, scrape, synthesize, critique.")

query = st.text_input("Research question", placeholder="e.g. What are the latest advances in solid-state batteries?")
run_clicked = st.button("Run Research", type="primary", disabled=not query.strip())

if run_clicked:
    graph = build_graph()
    initial_state = {
        "query": query.strip(),
        "search_results": [],
        "scraped_docs": [],
        "sources": [],
        "report_markdown": "",
        "report_title": "",
        "critique": None,
        "errors": [],
        "fatal_error": None,
    }

    final_state = dict(initial_state)

    with st.status("Running MARS pipeline...", expanded=True) as status:
        try:
            for update in graph.stream(initial_state, stream_mode="updates"):
                for node_name, partial_state in update.items():
                    final_state.update(partial_state)
                    label = STAGE_LABELS.get(node_name, f"Running {node_name}...")
                    status.write(label)
        except Exception as exc:
            final_state["fatal_error"] = f"Unexpected pipeline error: {exc}"

        if final_state.get("fatal_error"):
            status.update(label="Pipeline failed", state="error")
        else:
            status.update(label="Pipeline complete", state="complete")

    if final_state.get("fatal_error"):
        st.error(final_state["fatal_error"])
    else:
        try:
            pdf_bytes = generate_pdf_bytes(final_state)
        except Exception as exc:
            pdf_bytes = None
            st.error(f"PDF generation failed: {exc}")

        st.session_state["final_state"] = final_state
        st.session_state["pdf_bytes"] = pdf_bytes

if "final_state" in st.session_state:
    final_state = st.session_state["final_state"]
    pdf_bytes = st.session_state.get("pdf_bytes")

    if not final_state.get("fatal_error"):
        st.subheader(final_state.get("report_title") or "Research Report")

        word_count = len(final_state.get("report_markdown", "").split())
        source_count = len(final_state.get("sources", []))
        warning_count = len(final_state.get("errors", []))

        col1, col2, col3 = st.columns(3)
        col1.metric("Words", word_count)
        col2.metric("Sources used", source_count)
        col3.metric("Warnings", warning_count)

        if final_state.get("errors"):
            with st.expander(f"Warnings ({warning_count})"):
                for e in final_state["errors"]:
                    st.write(f"- {e}")

        critique = final_state.get("critique")
        if critique is not None:
            with st.expander("Critique", expanded=True):
                if critique.strengths or critique.weaknesses or critique.missing_angles or critique.citation_quality:
                    st.markdown(f"**Strengths**\n\n{critique.strengths}")
                    st.markdown(f"**Weaknesses**\n\n{critique.weaknesses}")
                    st.markdown(f"**Missing Angles**\n\n{critique.missing_angles}")
                    st.markdown(f"**Citation Quality**\n\n{critique.citation_quality}")
                else:
                    st.markdown(critique.raw_markdown)

        with st.expander("Preview report"):
            preview = final_state.get("report_markdown", "")[:500]
            st.markdown(preview + ("..." if len(final_state.get("report_markdown", "")) > 500 else ""))

        if pdf_bytes:
            st.download_button(
                "⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name="mars_research_report.pdf",
                mime="application/pdf",
            )
