"""Data models for Shopify collections."""

from __future__ import annotations

from pydantic import BaseModel


class CollectionSEO(BaseModel):
    """SEO metadata for a collection page."""

    meta_title: str = ""
    meta_description: str = ""
    body_html: str = ""


class CollectionPerformance(BaseModel):
    """GSC performance data for a collection URL."""

    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    average_position: float = 0.0
    top_queries: list[str] = []


class Collection(BaseModel):
    """Represents a Shopify collection with SEO data."""

    id: str
    handle: str
    title: str
    url: str = ""
    seo: CollectionSEO = CollectionSEO()
    performance: CollectionPerformance | None = None
    product_count: int = 0
    product_titles: list[str] = []

    @property
    def full_url(self) -> str:
        return self.url or f"/collections/{self.handle}"
