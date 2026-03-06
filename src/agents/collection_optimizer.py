"""Collection page SEO optimizer agent."""

from __future__ import annotations

import json
import logging

from mcp import ClientSession

from src.models.collection import Collection, CollectionSEO
from src.models.keyword import KeywordCluster
from src.utils.seo_helpers import (
    generate_meta_description,
    generate_meta_title,
    score_body_content,
    score_meta_description,
    score_meta_title,
)

logger = logging.getLogger(__name__)


class CollectionOptimizer:
    """Optimizes Shopify collection pages for SEO."""

    def __init__(self, shopify_session: ClientSession, site_domain: str):
        self.shopify = shopify_session
        self.site_domain = site_domain

    async def _call_tool(self, name: str, args: dict) -> dict:
        result = await self.shopify.call_tool(name, arguments=args)
        return json.loads(result.content[0].text)

    async def fetch_all_collections(self) -> list[Collection]:
        """Fetch all collections from Shopify."""
        logger.info("Fetching all collections from Shopify...")
        raw = await self._call_tool("list_collections", {"limit": 250})

        collections = []
        for item in raw:
            coll = Collection(
                id=item["id"],
                handle=item["handle"],
                title=item["title"],
                product_count=item.get("product_count", 0),
                seo=CollectionSEO(
                    meta_title=item.get("seo_title", ""),
                    meta_description=item.get("seo_description", ""),
                    body_html=item.get("body_html", ""),
                ),
            )
            collections.append(coll)

        logger.info("Found %d collections", len(collections))
        return collections

    def audit_collection(
        self,
        collection: Collection,
        keyword_cluster: KeywordCluster,
    ) -> dict:
        """Audit a collection page's current SEO status."""
        primary = keyword_cluster.primary_keyword.keyword
        title_score = score_meta_title(collection.seo.meta_title, primary)
        desc_score = score_meta_description(collection.seo.meta_description, primary)
        body_score = score_body_content(collection.seo.body_html, primary)

        overall = (title_score["score"] + desc_score["score"] + body_score["score"]) / 3

        return {
            "collection": collection.handle,
            "primary_keyword": primary,
            "overall_score": round(overall, 1),
            "title": title_score,
            "description": desc_score,
            "body": body_score,
        }

    def generate_optimized_seo(
        self,
        collection: Collection,
        keyword_cluster: KeywordCluster,
    ) -> CollectionSEO:
        """Generate optimized SEO metadata for a collection."""
        primary = keyword_cluster.primary_keyword.keyword
        brand = self.site_domain.split(".")[0].title() if self.site_domain else ""

        # Generate optimized title
        meta_title = generate_meta_title(primary, brand)

        # Generate optimized description
        product_context = ""
        if collection.product_titles:
            sample = ", ".join(collection.product_titles[:3])
            product_context = f"Featuring {sample} and more"
        meta_description = generate_meta_description(primary, product_context)

        # Generate improved body HTML
        secondary_keywords = keyword_cluster.long_tail_keywords[:3]
        secondary_text = ""
        if secondary_keywords:
            kw_list = [k.keyword for k in secondary_keywords]
            secondary_text = (
                f"<p>Whether you're looking for {kw_list[0]}"
                + (f", {kw_list[1]}" if len(kw_list) > 1 else "")
                + (f", or {kw_list[2]}" if len(kw_list) > 2 else "")
                + f", our {primary} collection has you covered.</p>"
            )

        body_html = (
            f"<h2>{collection.title}</h2>\n"
            f"<p>Discover our curated selection of {primary}. "
            f"We've handpicked the best products to help you find exactly what you need.</p>\n"
            f"{secondary_text}"
        )

        return CollectionSEO(
            meta_title=meta_title,
            meta_description=meta_description,
            body_html=body_html,
        )

    async def optimize_collection(
        self,
        collection: Collection,
        keyword_cluster: KeywordCluster,
        dry_run: bool = True,
    ) -> dict:
        """Optimize a single collection page.

        Returns a report with before/after SEO data.
        """
        logger.info("Optimizing collection: %s", collection.handle)

        # Audit current state
        before_audit = self.audit_collection(collection, keyword_cluster)

        # Generate optimized SEO
        optimized_seo = self.generate_optimized_seo(collection, keyword_cluster)

        # Apply changes (if not dry run)
        if not dry_run:
            await self._call_tool(
                "update_collection_seo",
                {
                    "collection_id": collection.id,
                    "meta_title": optimized_seo.meta_title,
                    "meta_description": optimized_seo.meta_description,
                    "body_html": optimized_seo.body_html,
                },
            )
            logger.info("Updated collection %s in Shopify", collection.handle)
        else:
            logger.info("[DRY RUN] Would update collection %s", collection.handle)

        return {
            "collection": collection.handle,
            "before_score": before_audit["overall_score"],
            "optimized_seo": {
                "meta_title": optimized_seo.meta_title,
                "meta_description": optimized_seo.meta_description,
                "body_html": optimized_seo.body_html,
            },
            "dry_run": dry_run,
        }

    async def optimize_all(
        self,
        collections: list[Collection],
        keyword_clusters: dict[str, KeywordCluster],
        dry_run: bool = True,
    ) -> list[dict]:
        """Optimize all collection pages."""
        results = []
        for collection in collections:
            cluster = keyword_clusters.get(collection.handle)
            if not cluster:
                logger.warning("No keyword data for %s, skipping", collection.handle)
                continue
            report = await self.optimize_collection(collection, cluster, dry_run)
            results.append(report)
        return results
