"""Scrape node: fetches and cleans full-text content for each search result URL."""
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

from state import MARSState, ScrapedDoc, SourceCitation

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
REQUEST_TIMEOUT = 10
MAX_CHARS = 6000
MIN_CONTENT_CHARS = 200
STRIP_TAGS = ["script", "style", "nav", "footer", "header", "aside"]


def _scrape_one(result) -> tuple:
    """Returns (ScrapedDoc | None, error_message | None)."""
    try:
        resp = requests.get(
            result.url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
    except requests.RequestException as exc:
        return None, f"Skipped {result.url}: {exc.__class__.__name__}"

    if resp.status_code != 200:
        return None, f"Skipped {result.url}: HTTP {resp.status_code}"

    content_type = resp.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return None, f"Skipped {result.url}: non-HTML content ({content_type or 'unknown'})"

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(STRIP_TAGS):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())
    except Exception as exc:
        return None, f"Skipped {result.url}: parse error ({exc.__class__.__name__})"

    if len(text) < MIN_CONTENT_CHARS:
        return None, f"Skipped {result.url}: too little extractable text (likely JS-rendered)"

    text = text[:MAX_CHARS]
    title = result.title or (soup.title.string.strip() if soup.title and soup.title.string else result.url)

    return ScrapedDoc(url=result.url, title=title, text=text, char_count=len(text)), None


def run_scrape(state: MARSState) -> dict:
    search_results = state.get("search_results", [])
    scraped_docs: list[ScrapedDoc] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_scrape_one, r): r for r in search_results}
        for future in as_completed(futures):
            try:
                doc, error = future.result()
            except Exception as exc:
                doc, error = None, f"Skipped {futures[future].url}: {exc}"
            if doc is not None:
                scraped_docs.append(doc)
            if error is not None:
                errors.append(error)

    # Keep original relevance order (as_completed scrambles it)
    order = {r.url: i for i, r in enumerate(search_results)}
    scraped_docs.sort(key=lambda d: order.get(d.url, 999))

    if not scraped_docs:
        errors.append(
            "All source pages failed to scrape; the report will fall back to search snippets only."
        )

    sources = [
        SourceCitation(id=i + 1, url=d.url, title=d.title)
        for i, d in enumerate(scraped_docs)
    ]

    return {
        "scraped_docs": scraped_docs,
        "sources": sources,
        "errors": state.get("errors", []) + errors,
    }
