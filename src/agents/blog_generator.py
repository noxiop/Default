"""Blog post generator for hub-and-spoke internal linking model."""

from __future__ import annotations

import json
import logging
import re

from mcp import ClientSession

from src.models.blog_post import BlogPost
from src.models.collection import Collection
from src.models.keyword import Keyword, KeywordCluster
from src.utils.linking import (
    build_hub_to_spoke_links,
    build_spoke_to_hub_link,
    build_spoke_to_spoke_links,
    inject_links_into_html,
)

logger = logging.getLogger(__name__)


class BlogGenerator:
    """Generates SEO-optimized blog posts in a hub-and-spoke model."""

    def __init__(self, shopify_session: ClientSession, site_url: str = ""):
        self.shopify = shopify_session
        self.site_url = site_url

    async def _call_tool(self, name: str, args: dict) -> dict:
        result = await self.shopify.call_tool(name, arguments=args)
        return json.loads(result.content[0].text)

    def _slugify(self, text: str) -> str:
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug.strip("-")

    def generate_blog_post_content(
        self,
        target_keyword: Keyword,
        collection: Collection,
        post_index: int,
    ) -> BlogPost:
        """Generate a single blog post targeting a long-tail keyword.

        Creates structured HTML content with proper headings, keyword usage,
        and placeholder content sections. In production, this would be
        enhanced with an LLM for actual content generation.
        """
        kw = target_keyword.keyword
        kw_title = kw.title()
        collection_title = collection.title

        handle = self._slugify(kw)
        title = f"{kw_title}: A Complete Guide"
        meta_title = f"{kw_title} - Tips & Guide | {collection_title}"
        if len(meta_title) > 60:
            meta_title = meta_title[:57] + "..."
        meta_description = (
            f"Learn everything about {kw.lower()}. Discover tips, recommendations, "
            f"and our top picks from our {collection_title.lower()} collection."
        )
        if len(meta_description) > 155:
            meta_description = meta_description[:152] + "..."

        body_html = f"""<p>{kw_title} is an important topic for anyone interested in {collection_title.lower()}. In this comprehensive guide, we'll cover everything you need to know about {kw.lower()}, from the basics to advanced tips.</p>

<h2>What is {kw_title}?</h2>
<p>Understanding {kw.lower()} is the first step toward making informed decisions. Whether you're a beginner or experienced, having a solid grasp of the fundamentals will help you choose the right products and approaches.</p>

<h2>Key Benefits of {kw_title}</h2>
<p>There are several advantages to understanding and leveraging {kw.lower()}:</p>
<ul>
<li>Make more informed purchasing decisions</li>
<li>Get better value for your investment</li>
<li>Stay ahead of trends and developments</li>
<li>Find products that truly match your needs</li>
</ul>

<h2>How to Choose the Best {kw_title}</h2>
<p>When selecting products related to {kw.lower()}, consider factors like quality, value, reviews, and how they fit your specific requirements. Our curated {collection_title.lower()} collection features top-rated options that have been vetted for quality and customer satisfaction.</p>

<h2>Expert Tips for {kw_title}</h2>
<p>Here are some insider tips to help you get the most out of {kw.lower()}:</p>
<ol>
<li>Research thoroughly before making a purchase</li>
<li>Read customer reviews and ratings</li>
<li>Compare options across different price points</li>
<li>Consider long-term value over short-term savings</li>
</ol>

<h2>Conclusion</h2>
<p>We hope this guide to {kw.lower()} has been helpful. Explore our full range of products to find exactly what you're looking for.</p>"""

        tags = [
            collection.handle,
            kw.lower().replace(" ", "-"),
            "guide",
            "seo",
        ]

        return BlogPost(
            title=title,
            handle=handle,
            target_keyword=kw,
            meta_title=meta_title,
            meta_description=meta_description,
            body_html=body_html,
            tags=tags,
            hub_collection_handle=collection.handle,
        )

    def generate_spoke_posts(
        self,
        collection: Collection,
        keyword_cluster: KeywordCluster,
        count: int = 5,
    ) -> list[BlogPost]:
        """Generate all spoke blog posts for a collection hub."""
        spoke_keywords = keyword_cluster.get_spoke_keywords(count)
        posts: list[BlogPost] = []

        for i, kw in enumerate(spoke_keywords):
            post = self.generate_blog_post_content(kw, collection, i)
            posts.append(post)

        # Now inject internal links into all posts
        for i, post in enumerate(posts):
            # Hub link: spoke -> collection
            hub_link = build_spoke_to_hub_link(
                collection.handle, collection.title, self.site_url
            )
            post.internal_links.append(hub_link)

            # Spoke-to-spoke cross links
            spoke_links = build_spoke_to_spoke_links(post, posts, max_links=2, site_url=self.site_url)
            post.internal_links.extend(spoke_links)

            # Inject links into the HTML
            post.body_html = inject_links_into_html(post.body_html, hub_link, spoke_links)

        logger.info(
            "Generated %d spoke blog posts for hub: %s",
            len(posts),
            collection.handle,
        )
        return posts

    async def publish_blog_posts(
        self,
        posts: list[BlogPost],
        dry_run: bool = True,
    ) -> list[dict]:
        """Publish blog posts to Shopify."""
        results = []
        for post in posts:
            if dry_run:
                logger.info("[DRY RUN] Would publish: %s", post.title)
                results.append({
                    "title": post.title,
                    "handle": post.handle,
                    "target_keyword": post.target_keyword,
                    "status": "dry_run",
                })
            else:
                try:
                    resp = await self._call_tool(
                        "create_blog_post",
                        {
                            "title": post.title,
                            "body_html": post.body_html,
                            "tags": ",".join(post.tags),
                            "meta_title": post.meta_title,
                            "meta_description": post.meta_description,
                        },
                    )
                    article = resp.get("article", {})
                    post.shopify_article_id = article.get("id")
                    post.handle = article.get("handle", post.handle)
                    results.append({
                        "title": post.title,
                        "handle": post.handle,
                        "target_keyword": post.target_keyword,
                        "shopify_id": post.shopify_article_id,
                        "status": "published",
                    })
                    logger.info("Published blog post: %s", post.title)
                except Exception as e:
                    logger.error("Failed to publish %s: %s", post.title, e)
                    results.append({
                        "title": post.title,
                        "target_keyword": post.target_keyword,
                        "status": "error",
                        "error": str(e),
                    })
        return results

    async def update_hub_with_spoke_links(
        self,
        collection: Collection,
        posts: list[BlogPost],
        dry_run: bool = True,
    ) -> dict:
        """Update the hub collection page to link to all spoke blog posts."""
        links_html = build_hub_to_spoke_links(
            collection.handle, posts, self.site_url
        )
        new_body = collection.seo.body_html + "\n" + links_html

        if dry_run:
            logger.info(
                "[DRY RUN] Would update hub %s with %d spoke links",
                collection.handle,
                len(posts),
            )
            return {"collection": collection.handle, "status": "dry_run", "spoke_count": len(posts)}

        await self._call_tool(
            "update_collection_seo",
            {
                "collection_id": collection.id,
                "meta_title": collection.seo.meta_title,
                "meta_description": collection.seo.meta_description,
                "body_html": new_body,
            },
        )
        logger.info("Updated hub %s with %d spoke links", collection.handle, len(posts))
        return {"collection": collection.handle, "status": "updated", "spoke_count": len(posts)}
