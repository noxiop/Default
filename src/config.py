"""Configuration management for the SEO agent."""

from __future__ import annotations

import os
import sys
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

    def validate_required(self) -> list[str]:
        """Check that all required fields have real values. Returns list of problems."""
        problems = []
        if not self.shopify.store_url or self.shopify.store_url.startswith("https://your-"):
            problems.append(
                "SHOPIFY_STORE_URL not set. "
                "Get this from your Shopify admin URL (e.g., https://my-store.myshopify.com)"
            )
        if not self.shopify.access_token or "xxxxx" in self.shopify.access_token:
            problems.append(
                "SHOPIFY_ACCESS_TOKEN not set. "
                "Create one in Shopify Admin > Settings > Apps > Develop apps"
            )
        if not self.shopify.blog_id:
            problems.append(
                "SHOPIFY_BLOG_ID not set. "
                "Find it in Shopify Admin > Online Store > Blog posts > check the URL"
            )
        if not self.gsc.site_url:
            problems.append(
                "GSC_SITE_URL not set. "
                "This is your verified property URL in Google Search Console"
            )
        if not self.semrush.api_key or self.semrush.api_key.startswith("your-"):
            problems.append(
                "SEMRUSH_API_KEY not set. "
                "Get your API key from SEMRush > Subscription Info > API Key"
            )
        return problems


def get_settings() -> Settings:
    """Load settings from environment. Exits with helpful message if .env is missing."""
    if not Path(".env").exists():
        print("\n  ERROR: No .env file found!")
        print("  This file contains your API credentials.")
        print()
        print("  Quick fix:")
        print("    1. cp .env.example .env")
        print("    2. Open .env in a text editor")
        print("    3. Replace the placeholder values with your real API keys")
        print()
        print("  Need help? Run: python -m src.verify_setup")
        print()
        sys.exit(1)
    return Settings()
