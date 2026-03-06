"""MCP Server for Google Search Console API integration.

Exposes tools for pulling search performance data, top queries,
and indexing status from GSC.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gsc")

CREDENTIALS_PATH = os.environ.get("GSC_CREDENTIALS_PATH", "")
SITE_URL = os.environ.get("GSC_SITE_URL", "")
GSC_API_BASE = "https://searchconsole.googleapis.com/webmasters/v3"

# In production, use google-auth library for proper OAuth2 flow.
# This simplified version expects a pre-obtained access token or
# service account credentials.
_access_token: str | None = None


async def _get_access_token() -> str:
    """Obtain an access token from service account credentials.

    In a full implementation, this uses google.oauth2.service_account
    to exchange the JSON key for a bearer token.
    """
    global _access_token
    if _access_token:
        return _access_token

    # Placeholder: in production, load CREDENTIALS_PATH and do OAuth2 exchange
    # For now, check if token is passed via env for simpler setups
    token = os.environ.get("GSC_ACCESS_TOKEN", "")
    if token:
        _access_token = token
        return token

    raise RuntimeError(
        "GSC credentials not configured. Set GSC_CREDENTIALS_PATH to a "
        "service account JSON file or GSC_ACCESS_TOKEN to a bearer token."
    )


async def _gsc_request(method: str, endpoint: str, body: dict | None = None) -> dict:
    token = await _get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{GSC_API_BASE}/{endpoint}"
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "POST":
            resp = await client.post(url, headers=headers, json=body or {})
        else:
            resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


def _default_date_range() -> tuple[str, str]:
    end = datetime.now() - timedelta(days=3)  # GSC data has ~3 day lag
    start = end - timedelta(days=90)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_search_performance(
    start_date: str = "",
    end_date: str = "",
    dimensions: str = "query",
    row_limit: int = 100,
) -> str:
    """Get overall search performance data (queries, clicks, impressions, CTR, position)."""
    if not start_date or not end_date:
        start_date, end_date = _default_date_range()

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions.split(","),
        "rowLimit": row_limit,
    }
    result = await _gsc_request(
        "POST", f"sites/{SITE_URL}/searchAnalytics/query", body
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_page_performance(page_url: str, row_limit: int = 50) -> str:
    """Get search performance for a specific page URL, broken down by query."""
    start_date, end_date = _default_date_range()
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "dimensionFilterGroups": [
            {
                "filters": [
                    {
                        "dimension": "page",
                        "operator": "equals",
                        "expression": page_url,
                    }
                ]
            }
        ],
        "rowLimit": row_limit,
    }
    result = await _gsc_request(
        "POST", f"sites/{SITE_URL}/searchAnalytics/query", body
    )
    rows = result.get("rows", [])
    return json.dumps(
        {
            "page": page_url,
            "queries": [
                {
                    "query": row["keys"][0],
                    "clicks": row["clicks"],
                    "impressions": row["impressions"],
                    "ctr": round(row["ctr"], 4),
                    "position": round(row["position"], 1),
                }
                for row in rows
            ],
        },
        indent=2,
    )


@mcp.tool()
async def get_top_queries(limit: int = 100) -> str:
    """Get top search queries for the entire site by clicks."""
    start_date, end_date = _default_date_range()
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "rowLimit": limit,
    }
    result = await _gsc_request(
        "POST", f"sites/{SITE_URL}/searchAnalytics/query", body
    )
    rows = result.get("rows", [])
    queries = [
        {
            "query": row["keys"][0],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": round(row["ctr"], 4),
            "position": round(row["position"], 1),
        }
        for row in rows
    ]
    return json.dumps(queries, indent=2)


@mcp.tool()
async def get_indexing_status(page_url: str) -> str:
    """Check the indexing status of a specific URL."""
    result = await _gsc_request(
        "GET",
        f"sites/{SITE_URL}/urlInspection/index:inspect",
    )
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
