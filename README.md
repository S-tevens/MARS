# MARS — Multi-Agent Research Assistant Platform

MARS turns a research question into a structured, citation-backed report. A LangGraph-orchestrated
pipeline of four agents searches the web, scrapes and cleans the source pages, drafts a synthesized
report with Google Gemini, and critiques its own draft — all surfaced through a Streamlit UI with a
downloadable PDF as the final deliverable.

## Architecture

```
                 ┌──────────┐   fatal error   
   START ──────▶ │  search  │ ───────────────▶ END
                 └────┬─────┘
                      │ ok
                      ▼
                 ┌──────────┐
                 │  scrape  │  (never fatal — bad pages are skipped, not fatal)
                 └────┬─────┘
                      ▼
                 ┌──────────┐   fatal error
                 │  report  │ ───────────────▶ END
                 └────┬─────┘
                      │ ok
                      ▼
                 ┌──────────┐
                 │ critique │  (failures caught internally, never fatal)
                 └────┬─────┘
                      ▼
                     END
```

- **Search agent** (`agents/search_agent.py`) — queries the [Tavily](https://tavily.com) search API.
- **Scrape agent** (`agents/scrape_agent.py`) — fetches each result with `requests` and extracts clean
  body text with BeautifulSoup, skipping any page that fails, blocks bots, or is too JS-heavy to parse.
- **Report agent** (`agents/report_agent.py`) — prompts Google Gemini to synthesize a themed,
  inline-cited report from the scraped excerpts (falls back to search snippets if every scrape fails).
- **Critique agent** (`agents/critique_agent.py`) — a single Gemini pass reviewing the report for
  strengths, weaknesses, missing angles, and citation quality.

## Tech stack

LangChain · LangGraph · `langchain-google-genai` (Gemini) · Tavily Search · BeautifulSoup4 · Streamlit ·
`fpdf2` for PDF export · `python-dotenv` for config.

## Setup (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If activation is blocked by execution policy, run once:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then install dependencies and configure keys:

```powershell
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and fill in:
- `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/apikey).
- `TAVILY_API_KEY` — free tier (~1000 searches/month) from [tavily.com](https://tavily.com).
- `GEMINI_MODEL` — verify the current model id at
  [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) before first run,
  since Google periodically retires older model names.

## Run

```powershell
streamlit run app.py
```

Enter a research question, click **Run Research**, and watch each stage complete live. When the
pipeline finishes you'll see the report title, word/source/warning counts, the critique, a short
preview, and a **Download PDF Report** button.

## Project structure

```
MARS/
├── app.py                 # Streamlit UI entrypoint
├── graph.py                # LangGraph StateGraph wiring
├── state.py                 # Shared pipeline state schema
├── config.py                # Env loading + validation
├── pdf_export.py            # Report -> PDF (fpdf2)
└── agents/
    ├── search_agent.py
    ├── scrape_agent.py
    ├── report_agent.py
    └── critique_agent.py
```

## Why LangGraph instead of a plain chain?

The pipeline has real branch points — a failed search or an empty Gemini response should short-circuit
the run, while a failed page scrape or a failed critique call should not. LangGraph's `StateGraph` makes
those success/failure paths explicit as conditional edges over a single shared state object, rather than
scattering `if`/`try` control flow through a linear script. It also gives the Streamlit UI free real-time
progress via `graph.stream(..., stream_mode="updates")`, since each node's output is yielded as it
completes.

## Known limitations

- The critique step is a single pass — it does not feed back into a report revision loop.
- Scraping uses `requests` + BeautifulSoup only, so JavaScript-rendered (SPA) pages that don't return
  meaningful HTML are skipped rather than rendered.
- The PDF export uses core PDF fonts (Latin-1), so non-Latin scripts in Gemini's output are not fully
  supported.

## License

MIT
