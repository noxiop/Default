"""MCP Server for SEMRush API integration.

Exposes tools for keyword research, competitor analysis, and
backlink data from SEMRush.
"""

from __future__ import annotations

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("semrush")

API_KEY = os.environ.get("SEMRUSH_API_KEY", "")
SEMRUSH_API_BASE = "https://api.semrush.com"


async def _semrush_request(params: dict) -> str:
    params["key"] = API_KEY
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(SEMRUSH_API_BASE, params=params)
        resp.raise_for_status()
        return resp.text


def _parse_semrush_csv(raw: str) -> list[dict]:
    """Parse SEMRush's semicolon-delimited response format."""
    lines = raw.strip().split("\n")
    if len(lines) < 2:
        return []
    headers = lines[0].split(";")
    rows = []
    for line in lines[1:]:
        values = line.split(";")
        rows.append(dict(zip(headers, values)))
    return rows


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_domain_keywords(
    domain: str,
    database: str = "us",
    limit: int = 100,
) -> str:
    """Get organic keywords that a domain ranks for."""
    raw = await _semrush_request({
        "type": "domain_organic",
        "domain": domain,
        "database": database,
        "display_limit": limit,
        "export_columns": "Ph,Po,Nq,Cp,Kd,Ur",
    })
    rows = _parse_semrush_csv(raw)
    keywords = [
        {
            "keyword": r.get("Ph", ""),
            "position": int(r.get("Po", 0)),
            "search_volume": int(r.get("Nq", 0)),
            "cpc": float(r.get("Cp", 0)),
            "keyword_difficulty": float(r.get("Kd", 0)),
            "url": r.get("Ur", ""),
        }
        for r in rows
    ]
    return json.dumps(keywords, indent=2)


@mcp.tool()
async def get_keyword_data(keyword: str, database: str = "us") -> str:
    """Get search volume, difficulty, and CPC for a specific keyword."""
    raw = await _semrush_request({
        "type": "phrase_all",
        "phrase": keyword,
        "database": database,
        "export_columns": "Ph,Nq,Cp,Co,Kd,Nr",
    })
    rows = _parse_semrush_csv(raw)
    if not rows:
        return json.dumps({"error": f"No data found for '{keyword}'"})
    r = rows[0]
    return json.dumps({
        "keyword": r.get("Ph", keyword),
        "search_volume": int(r.get("Nq", 0)),
        "cpc": float(r.get("Cp", 0)),
        "competition": float(r.get("Co", 0)),
        "keyword_difficulty": float(r.get("Kd", 0)),
        "results_count": int(r.get("Nr", 0)),
    }, indent=2)


@mcp.tool()
async def get_keyword_suggestions(
    keyword: str,
    database: str = "us",
    limit: int = 50,
) -> str:
    """Get related/long-tail keyword suggestions for a seed keyword."""
    raw = await _semrush_request({
        "type": "phrase_related",
        "phrase": keyword,
        "database": database,
        "display_limit": limit,
        "export_columns": "Ph,Nq,Cp,Co,Kd",
    })
    rows = _parse_semrush_csv(raw)
    suggestions = [
        {
            "keyword": r.get("Ph", ""),
            "search_volume": int(r.get("Nq", 0)),
            "cpc": float(r.get("Cp", 0)),
            "competition": float(r.get("Co", 0)),
            "keyword_difficulty": float(r.get("Kd", 0)),
        }
        for r in rows
    ]
    return json.dumps(suggestions, indent=2)


@mcp.tool()
async def get_competitor_keywords(
    domain: str,
    competitor_domain: str,
    database: str = "us",
    limit: int = 50,
) -> str:
    """Get keywords that a competitor ranks for but the target domain doesn't."""
    raw = await _semrush_request({
        "type": "domain_domains",
        "domains": f"{domain}|or|{competitor_domain}|or",
        "database": database,
        "display_limit": limit,
        "export_columns": "Ph,Nq,Cp,Kd,Co",
    })
    rows = _parse_semrush_csv(raw)
    gaps = [
        {
            "keyword": r.get("Ph", ""),
            "search_volume": int(r.get("Nq", 0)),
            "cpc": float(r.get("Cp", 0)),
            "keyword_difficulty": float(r.get("Kd", 0)),
        }
        for r in rows
    ]
    return json.dumps(gaps, indent=2)


@mcp.tool()
async def get_backlink_data(target: str, limit: int = 50) -> str:
    """Get backlink data for a URL or domain."""
    raw = await _semrush_request({
        "type": "backlinks_overview",
        "target": target,
        "target_type": "root_domain",
        "export_columns": "total,domains_num,urls_num,ips_num,follows_num,nofollows_num",
    })
    rows = _parse_semrush_csv(raw)
    if not rows:
        return json.dumps({"error": f"No backlink data for '{target}'"})
    r = rows[0]
    return json.dumps({
        "total_backlinks": int(r.get("total", 0)),
        "referring_domains": int(r.get("domains_num", 0)),
        "referring_urls": int(r.get("urls_num", 0)),
        "follow_links": int(r.get("follows_num", 0)),
        "nofollow_links": int(r.get("nofollows_num", 0)),
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
