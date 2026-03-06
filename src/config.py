"""Configuration management for the SEO agent."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class ShopifyConfig(BaseModel):
    store_url: str = os.getenv("SHOPIFY_STORE_URL", "")
    access_token: str = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    blog_id: str = os.getenv("SHOPIFY_BLOG_ID", "")
    api_version: str = "2024-01"


class GSCConfig(BaseModel):
    credentials_path: str = os.getenv("GSC_CREDENTIALS_PATH", "")
    site_url: str = os.getenv("GSC_SITE_URL", "")


class SEMRushConfig(BaseModel):
    api_key: str = os.getenv("SEMRUSH_API_KEY", "")


class AgentConfig(BaseModel):
    dry_run: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    blog_posts_per_collection: int = int(os.getenv("BLOG_POSTS_PER_COLLECTION", "5"))
    target_blog_word_count: int = int(os.getenv("TARGET_BLOG_WORD_COUNT", "1000"))


class Settings(BaseModel):
    shopify: ShopifyConfig = ShopifyConfig()
    gsc: GSCConfig = GSCConfig()
    semrush: SEMRushConfig = SEMRushConfig()
    agent: AgentConfig = AgentConfig()


def get_settings() -> Settings:
    return Settings()
