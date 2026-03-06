"""Tests for blog post generation and linking."""

from src.agents.blog_generator import BlogGenerator
from src.models.blog_post import BlogPost, InternalLink
from src.models.collection import Collection, CollectionSEO
from src.models.keyword import Keyword, KeywordCluster
from src.utils.linking import (
    build_hub_to_spoke_links,
    build_spoke_to_hub_link,
    build_spoke_to_spoke_links,
    inject_links_into_html,
)


def _make_collection() -> Collection:
    return Collection(
        id="gid://shopify/Collection/1",
        handle="running-shoes",
        title="Running Shoes",
        seo=CollectionSEO(),
        product_count=20,
    )


def _make_cluster() -> KeywordCluster:
    return KeywordCluster(
        primary_keyword=Keyword(keyword="running shoes", search_volume=5000),
        long_tail_keywords=[
            Keyword(keyword="best running shoes for beginners", search_volume=800, keyword_difficulty=20),
            Keyword(keyword="running shoes for flat feet", search_volume=600, keyword_difficulty=15),
            Keyword(keyword="lightweight running shoes", search_volume=500, keyword_difficulty=25),
            Keyword(keyword="trail running shoes guide", search_volume=400, keyword_difficulty=10),
            Keyword(keyword="running shoe reviews 2024", search_volume=300, keyword_difficulty=30),
        ],
        collection_handle="running-shoes",
    )


def test_generate_spoke_posts():
    gen = BlogGenerator.__new__(BlogGenerator)
    gen.site_url = "https://example.com"

    collection = _make_collection()
    cluster = _make_cluster()

    posts = gen.generate_spoke_posts(collection, cluster, count=5)

    assert len(posts) == 5
    for post in posts:
        assert post.title
        assert post.handle
        assert post.target_keyword
        assert post.body_html
        assert post.meta_title
        assert len(post.meta_title) <= 60
        assert post.meta_description
        assert len(post.meta_description) <= 155
        # Each spoke should have a hub link
        hub_links = [l for l in post.internal_links if l.link_type == "spoke_to_hub"]
        assert len(hub_links) >= 1
        assert "/collections/running-shoes" in hub_links[0].url


def test_build_hub_to_spoke_links():
    posts = [
        BlogPost(title="Post 1", handle="post-1", target_keyword="kw1"),
        BlogPost(title="Post 2", handle="post-2", target_keyword="kw2"),
    ]
    html = build_hub_to_spoke_links("shoes", posts)
    assert "Post 1" in html
    assert "Post 2" in html
    assert "/blogs/news/post-1" in html


def test_build_spoke_to_hub_link():
    link = build_spoke_to_hub_link("shoes", "Running Shoes", "https://example.com")
    assert link.url == "https://example.com/collections/shoes"
    assert link.anchor_text == "Running Shoes"
    assert link.link_type == "spoke_to_hub"


def test_build_spoke_to_spoke_links():
    posts = [
        BlogPost(title="Post A", handle="post-a", target_keyword="kw-a"),
        BlogPost(title="Post B", handle="post-b", target_keyword="kw-b"),
        BlogPost(title="Post C", handle="post-c", target_keyword="kw-c"),
    ]
    links = build_spoke_to_spoke_links(posts[0], posts, max_links=2)
    assert len(links) == 2
    assert all(l.link_type == "spoke_to_spoke" for l in links)
    # Should not link to self
    assert all("post-a" not in l.url for l in links)


def test_inject_links_into_html():
    html = "<p>This is the first paragraph.</p><p>Second paragraph.</p>"
    hub_link = InternalLink(url="/collections/shoes", anchor_text="Running Shoes")
    spoke_links = [
        InternalLink(url="/blogs/news/post-b", anchor_text="Post B", link_type="spoke_to_spoke"),
    ]
    result = inject_links_into_html(html, hub_link, spoke_links)
    assert "/collections/shoes" in result
    assert "Running Shoes" in result
    assert "Related Articles" in result
    assert "Post B" in result
