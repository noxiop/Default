"""Data models for blog posts."""

from __future__ import annotations

from pydantic import BaseModel


class InternalLink(BaseModel):
    """An internal link within content."""

    url: str
    anchor_text: str
    link_type: str = "spoke_to_hub"  # spoke_to_hub, spoke_to_spoke, hub_to_spoke


class BlogPost(BaseModel):
    """A blog post for the hub-and-spoke model."""

    title: str
    handle: str = ""
    target_keyword: str
    meta_title: str = ""
    meta_description: str = ""
    body_html: str = ""
    tags: list[str] = []
    internal_links: list[InternalLink] = []
    hub_collection_handle: str = ""
    shopify_article_id: str | None = None

    @property
    def url(self) -> str:
        return f"/blogs/news/{self.handle}" if self.handle else ""
