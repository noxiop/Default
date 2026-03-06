"""Tests for the collection optimizer agent."""

from src.agents.collection_optimizer import CollectionOptimizer
from src.models.collection import Collection, CollectionSEO
from src.models.keyword import Keyword, KeywordCluster


def _make_collection(handle: str = "test-collection", title: str = "Test Collection") -> Collection:
    return Collection(
        id="gid://shopify/Collection/1",
        handle=handle,
        title=title,
        seo=CollectionSEO(
            meta_title="Old Title",
            meta_description="Old description",
            body_html="<p>Old body</p>",
        ),
        product_count=10,
        product_titles=["Product A", "Product B", "Product C"],
    )


def _make_cluster(keyword: str = "test widgets") -> KeywordCluster:
    return KeywordCluster(
        primary_keyword=Keyword(keyword=keyword, search_volume=1000, keyword_difficulty=30),
        long_tail_keywords=[
            Keyword(keyword="best test widgets", search_volume=500, keyword_difficulty=20),
            Keyword(keyword="cheap test widgets", search_volume=300, keyword_difficulty=15),
            Keyword(keyword="test widgets guide", search_volume=200, keyword_difficulty=10),
        ],
        collection_handle="test-collection",
    )


def test_audit_collection():
    optimizer = CollectionOptimizer.__new__(CollectionOptimizer)
    optimizer.site_domain = "example.com"

    collection = _make_collection()
    cluster = _make_cluster()

    audit = optimizer.audit_collection(collection, cluster)

    assert "overall_score" in audit
    assert "title" in audit
    assert "description" in audit
    assert "body" in audit
    assert audit["primary_keyword"] == "test widgets"


def test_generate_optimized_seo():
    optimizer = CollectionOptimizer.__new__(CollectionOptimizer)
    optimizer.site_domain = "example.com"

    collection = _make_collection()
    cluster = _make_cluster()

    seo = optimizer.generate_optimized_seo(collection, cluster)

    assert "test widgets" in seo.meta_title.lower() or "Test Widgets" in seo.meta_title
    assert len(seo.meta_title) <= 60
    assert len(seo.meta_description) <= 155
    assert seo.body_html  # Not empty
