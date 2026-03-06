"""MCP Server for Shopify Admin API integration.

Exposes tools for reading and updating Shopify collections and blog posts.
Connects via the Shopify Admin GraphQL API.
"""

from __future__ import annotations

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("shopify")

STORE_URL = os.environ.get("SHOPIFY_STORE_URL", "")
ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "")
API_VERSION = "2024-01"


def _graphql_url() -> str:
    return f"{STORE_URL}/admin/api/{API_VERSION}/graphql.json"


def _headers() -> dict[str, str]:
    return {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


async def _graphql(query: str, variables: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = await client.post(_graphql_url(), headers=_headers(), json=payload)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_collections(limit: int = 50) -> str:
    """List all Shopify collections with their SEO metadata."""
    query = """
    query($limit: Int!) {
      collections(first: $limit) {
        edges {
          node {
            id
            handle
            title
            productsCount
            seo {
              title
              description
            }
            descriptionHtml
          }
        }
      }
    }
    """
    result = await _graphql(query, {"limit": limit})
    collections = []
    for edge in result.get("data", {}).get("collections", {}).get("edges", []):
        node = edge["node"]
        collections.append({
            "id": node["id"],
            "handle": node["handle"],
            "title": node["title"],
            "product_count": node.get("productsCount", 0),
            "seo_title": node.get("seo", {}).get("title", ""),
            "seo_description": node.get("seo", {}).get("description", ""),
            "body_html": node.get("descriptionHtml", ""),
        })
    return json.dumps(collections, indent=2)


@mcp.tool()
async def get_collection(handle: str) -> str:
    """Get a single collection by handle with full details."""
    query = """
    query($handle: String!) {
      collectionByHandle(handle: $handle) {
        id
        handle
        title
        productsCount
        seo { title description }
        descriptionHtml
        products(first: 20) {
          edges { node { title } }
        }
      }
    }
    """
    result = await _graphql(query, {"handle": handle})
    coll = result.get("data", {}).get("collectionByHandle")
    if not coll:
        return json.dumps({"error": f"Collection '{handle}' not found"})
    product_titles = [
        e["node"]["title"]
        for e in coll.get("products", {}).get("edges", [])
    ]
    return json.dumps({
        "id": coll["id"],
        "handle": coll["handle"],
        "title": coll["title"],
        "product_count": coll.get("productsCount", 0),
        "seo_title": coll.get("seo", {}).get("title", ""),
        "seo_description": coll.get("seo", {}).get("description", ""),
        "body_html": coll.get("descriptionHtml", ""),
        "product_titles": product_titles,
    }, indent=2)


@mcp.tool()
async def update_collection_seo(
    collection_id: str,
    meta_title: str,
    meta_description: str,
    body_html: str,
) -> str:
    """Update a collection's SEO title, description, and body HTML."""
    mutation = """
    mutation($input: CollectionInput!) {
      collectionUpdate(input: $input) {
        collection {
          id
          handle
          seo { title description }
        }
        userErrors { field message }
      }
    }
    """
    variables = {
        "input": {
            "id": collection_id,
            "seo": {
                "title": meta_title,
                "description": meta_description,
            },
            "descriptionHtml": body_html,
        }
    }
    result = await _graphql(mutation, variables)
    return json.dumps(result.get("data", {}).get("collectionUpdate", {}), indent=2)


@mcp.tool()
async def create_blog_post(
    title: str,
    body_html: str,
    tags: str = "",
    meta_title: str = "",
    meta_description: str = "",
) -> str:
    """Create a new blog article in Shopify."""
    mutation = """
    mutation($article: ArticleCreateInput!) {
      articleCreate(article: $article) {
        article {
          id
          handle
          title
        }
        userErrors { field message }
      }
    }
    """
    article_input: dict = {
        "blogId": f"gid://shopify/Blog/{BLOG_ID}",
        "title": title,
        "body": body_html,
        "isPublished": True,
    }
    if tags:
        article_input["tags"] = tags.split(",")
    if meta_title or meta_description:
        article_input["seo"] = {}
        if meta_title:
            article_input["seo"]["title"] = meta_title
        if meta_description:
            article_input["seo"]["description"] = meta_description

    result = await _graphql(mutation, {"article": article_input})
    return json.dumps(result.get("data", {}).get("articleCreate", {}), indent=2)


@mcp.tool()
async def list_products_in_collection(handle: str, limit: int = 50) -> str:
    """List product titles in a collection (for content context)."""
    query = """
    query($handle: String!, $limit: Int!) {
      collectionByHandle(handle: $handle) {
        products(first: $limit) {
          edges { node { title productType vendor tags } }
        }
      }
    }
    """
    result = await _graphql(query, {"handle": handle, "limit": limit})
    coll = result.get("data", {}).get("collectionByHandle")
    if not coll:
        return json.dumps({"error": f"Collection '{handle}' not found"})
    products = [e["node"] for e in coll.get("products", {}).get("edges", [])]
    return json.dumps(products, indent=2)


if __name__ == "__main__":
    mcp.run()
