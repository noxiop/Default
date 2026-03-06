"""Tests for keyword research models."""

from src.models.keyword import Keyword, KeywordCluster


def test_get_spoke_keywords_selects_best():
    cluster = KeywordCluster(
        primary_keyword=Keyword(keyword="shoes", search_volume=10000),
        long_tail_keywords=[
            Keyword(keyword="best running shoes", search_volume=500, keyword_difficulty=20),
            Keyword(keyword="cheap running shoes", search_volume=300, keyword_difficulty=10),
            Keyword(keyword="running shoes review", search_volume=800, keyword_difficulty=50),
            Keyword(keyword="top running shoes 2024", search_volume=400, keyword_difficulty=15),
            Keyword(keyword="running shoes guide", search_volume=200, keyword_difficulty=5),
            Keyword(keyword="marathon shoes", search_volume=600, keyword_difficulty=40),
        ],
    )
    spokes = cluster.get_spoke_keywords(5)
    assert len(spokes) == 5
    # The keyword with best volume/difficulty ratio should be first
    # "running shoes guide": 200/5 = 40
    assert spokes[0].keyword == "running shoes guide"


def test_get_spoke_keywords_handles_fewer_than_requested():
    cluster = KeywordCluster(
        primary_keyword=Keyword(keyword="shoes"),
        long_tail_keywords=[
            Keyword(keyword="best shoes", search_volume=100, keyword_difficulty=10),
        ],
    )
    spokes = cluster.get_spoke_keywords(5)
    assert len(spokes) == 1
