"""Shared state schema for the MARS LangGraph pipeline."""
from typing import List, Optional, TypedDict

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    score: float = 0.0


class ScrapedDoc(BaseModel):
    url: str
    title: str
    text: str
    char_count: int


class SourceCitation(BaseModel):
    id: int
    url: str
    title: str


class Critique(BaseModel):
    strengths: str = ""
    weaknesses: str = ""
    missing_angles: str = ""
    citation_quality: str = ""
    raw_markdown: str = ""


class MARSState(TypedDict, total=False):
    query: str
    search_results: List[SearchResult]
    scraped_docs: List[ScrapedDoc]
    sources: List[SourceCitation]
    report_markdown: str
    report_title: str
    critique: Optional[Critique]
    errors: List[str]
    fatal_error: Optional[str]
