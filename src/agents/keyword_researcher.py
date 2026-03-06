"""Keyword research agent using SEMRush and GSC data."""

from __future__ import annotations

import json
import logging

from mcp import ClientSession

from src.models.collection import Collection
from src.models.keyword import Keyword, KeywordCluster

logger = logging.getLogger(__name__)


class KeywordResearcher:
    """Researches keywords for collection pages using SEMRush + GSC data."""

    def __init__(
        self,
        semrush_session: ClientSession,
        gsc_session: ClientSession,
        site_domain: str,
    ):
        self.semrush = semrush_session
        self.gsc = gsc_session
        self.site_domain = site_domain

    async def _call_tool(self, session: ClientSession, name: str, args: dict) -> dict:
        result = await session.call_tool(name, arguments=args)
        return json.loads(result.content[0].text)

    async def research_collection(
        self,
        collection: Collection,
        long_tail_count: int = 20,
    ) -> KeywordCluster:
        """Research keywords for a single collection page.

        1. Pull existing GSC queries for this page
        2. Get SEMRush keyword suggestions based on collection title
        3. Build a keyword cluster with primary + long-tail keywords
        """
        logger.info("Researching keywords for collection: %s", collection.handle)

        # Step 1: Get GSC data for this collection URL
        gsc_queries: list[dict] = []
        try:
            page_url = f"https://{self.site_domain}/collections/{collection.handle}"
            gsc_data = await self._call_tool(
                self.gsc,
                "get_page_performance",
                {"page_url": page_url},
            )
            gsc_queries = gsc_data.get("queries", [])
        except Exception as e:
            logger.warning("Failed to get GSC data for %s: %s", collection.handle, e)

        # Step 2: Get SEMRush keyword suggestions
        seed_keyword = collection.title.lower()
        semrush_suggestions: list[dict] = []
        try:
            semrush_suggestions = await self._call_tool(
                self.semrush,
                "get_keyword_suggestions",
                {"keyword": seed_keyword, "limit": long_tail_count},
            )
            if isinstance(semrush_suggestions, dict) and "error" in semrush_suggestions:
                semrush_suggestions = []
        except Exception as e:
            logger.warning("Failed to get SEMRush suggestions for %s: %s", seed_keyword, e)

        # Step 3: Determine primary keyword from GSC data
        primary = Keyword(keyword=seed_keyword)
        if gsc_queries:
            top = gsc_queries[0]
            primary = Keyword(
                keyword=top["query"],
                search_volume=top.get("impressions", 0),
                current_position=int(top.get("position", 0)),
            )

        # Step 4: Build long-tail keyword list
        long_tails: list[Keyword] = []
        for s in semrush_suggestions:
            long_tails.append(
                Keyword(
                    keyword=s.get("keyword", ""),
                    search_volume=s.get("search_volume", 0),
                    keyword_difficulty=s.get("keyword_difficulty", 0),
                    cpc=s.get("cpc", 0),
                )
            )

        # Also include GSC queries as potential long-tails
        gsc_keywords_set = {lt.keyword.lower() for lt in long_tails}
        for q in gsc_queries[1:]:  # Skip first (used as primary)
            if q["query"].lower() not in gsc_keywords_set:
                long_tails.append(
                    Keyword(
                        keyword=q["query"],
                        search_volume=q.get("impressions", 0),
                        current_position=int(q.get("position", 0)),
                    )
                )

        return KeywordCluster(
            primary_keyword=primary,
            long_tail_keywords=long_tails,
            collection_handle=collection.handle,
        )

    async def research_all_collections(
        self,
        collections: list[Collection],
    ) -> dict[str, KeywordCluster]:
        """Research keywords for all collections. Returns mapping of handle -> cluster."""
        results = {}
        for collection in collections:
            cluster = await self.research_collection(collection)
            results[collection.handle] = cluster
        return results
