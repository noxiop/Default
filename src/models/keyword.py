"""Data models for keyword research."""

from __future__ import annotations

from pydantic import BaseModel


class Keyword(BaseModel):
    """A keyword with SEO metrics."""

    keyword: str
    search_volume: int = 0
    keyword_difficulty: float = 0.0
    cpc: float = 0.0
    intent: str = ""  # informational, transactional, navigational, commercial
    current_position: int | None = None


class KeywordCluster(BaseModel):
    """A cluster of related keywords for hub-and-spoke strategy."""

    primary_keyword: Keyword
    long_tail_keywords: list[Keyword] = []
    collection_handle: str = ""

    def get_spoke_keywords(self, count: int = 5) -> list[Keyword]:
        """Select the best long-tail keywords for spoke blog posts.

        Prioritizes keywords with decent volume but lower difficulty.
        """
        scored = sorted(
            self.long_tail_keywords,
            key=lambda k: (k.search_volume / max(k.keyword_difficulty, 1)),
            reverse=True,
        )
        return scored[:count]
