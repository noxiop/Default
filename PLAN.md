# Shopify SEO Automation Agent - Architecture Plan

## Overview

An automated SEO agent that connects to **Shopify**, **Google Search Console (GSC)**, and **SEMRush** via MCP (Model Context Protocol) servers to:

1. Audit and optimize all existing Shopify collection pages
2. Generate 5 supporting blog posts per collection in a **hub-and-spoke** internal linking model

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SEO Agent Orchestrator                │
│              (Python - main pipeline runner)            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Collection   │  │   Keyword    │  │  Blog Post   │  │
│  │  Optimizer    │  │  Researcher  │  │  Generator   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │           │
├─────────┴─────────────────┴─────────────────┴───────────┤
│                    MCP Client Layer                      │
│            (Connects to all 3 MCP servers)              │
├──────────┬────────────────┬─────────────────┬───────────┤
│          │                │                 │           │
│  ┌───────▼──────┐ ┌──────▼───────┐ ┌───────▼──────┐   │
│  │  Shopify MCP  │ │   GSC MCP    │ │ SEMRush MCP  │   │
│  │   Server      │ │   Server     │ │   Server     │   │
│  └───────┬──────┘ └──────┬───────┘ └───────┬──────┘   │
│          │               │                 │           │
└──────────┼───────────────┼─────────────────┼───────────┘
           │               │                 │
    ┌──────▼──────┐ ┌──────▼───────┐ ┌───────▼──────┐
    │  Shopify     │ │  Google      │ │  SEMRush     │
    │  Admin API   │ │  Search API  │ │  API         │
    └─────────────┘ └──────────────┘ └──────────────┘
```

---

## Hub-and-Spoke Model

```
                    ┌─────────────────────┐
                    │  Collection Page    │
                    │  (HUB)              │
                    │  /collections/xyz   │
                    └──────────┬──────────┘
                               │
            ┌──────┬───────┬───┴───┬───────┬──────┐
            │      │       │       │       │      │
         ┌──▼──┐┌──▼──┐┌───▼──┐┌──▼──┐┌───▼──┐
         │Blog ││Blog ││Blog  ││Blog ││Blog  │
         │  1  ││  2  ││  3   ││  4  ││  5   │
         │SPOKE││SPOKE││SPOKE ││SPOKE││SPOKE │
         └─────┘└─────┘└──────┘└─────┘└──────┘

Each spoke blog post:
  - Targets a long-tail keyword related to the collection
  - Links back to the collection page (hub) with optimized anchor text
  - Cross-links to 1-2 other spoke posts for topical reinforcement

The hub collection page:
  - Gets updated meta title, description, and body content
  - Links out to all 5 spoke blog posts
```

---

## MCP Server Details

### 1. Shopify MCP Server
- **Connection**: Shopify Admin GraphQL API via access token
- **Capabilities**:
  - `list_collections` - Fetch all collection pages
  - `get_collection` - Get single collection with SEO metadata
  - `update_collection_seo` - Update title, description, body HTML
  - `create_blog_post` - Create article in Shopify blog
  - `update_blog_post` - Update article content and SEO fields
  - `list_products_in_collection` - Get products for content context

### 2. Google Search Console MCP Server
- **Connection**: GSC API via OAuth2 service account
- **Capabilities**:
  - `get_search_performance` - Queries, clicks, impressions, CTR, position
  - `get_page_performance` - Performance data for specific URLs
  - `get_top_queries` - Top search queries for the site
  - `get_indexing_status` - Check indexation of pages

### 3. SEMRush MCP Server
- **Connection**: SEMRush API via API key
- **Capabilities**:
  - `get_domain_keywords` - Keywords the domain ranks for
  - `get_keyword_data` - Volume, difficulty, CPC for keywords
  - `get_keyword_suggestions` - Related/long-tail keyword ideas
  - `get_competitor_keywords` - Keywords competitors rank for
  - `get_backlink_data` - Backlink profile for pages

---

## Pipeline Steps

### Phase 1: Data Collection
1. Connect to Shopify → fetch all collections with metadata
2. Connect to GSC → pull performance data for each collection URL
3. Connect to SEMRush → get keyword data and opportunities

### Phase 2: Collection Page Optimization
For each collection page:
1. Analyze current title tag, meta description, H1, body content
2. Cross-reference with GSC impressions/clicks and SEMRush keyword data
3. Identify primary keyword (highest volume + relevance)
4. Generate optimized:
   - Meta title (≤60 chars, primary keyword front-loaded)
   - Meta description (≤155 chars, includes CTA)
   - Collection description/body HTML with keyword-rich content
5. Push updates to Shopify via MCP

### Phase 3: Blog Post Generation (Hub & Spoke)
For each collection (hub):
1. Use SEMRush to find 5 long-tail keywords related to the collection topic
2. For each long-tail keyword, generate a blog post:
   - SEO-optimized title
   - 800-1200 word article with proper H2/H3 structure
   - Internal link back to collection page (hub) with varied anchor text
   - Cross-links to 1-2 other spoke posts
3. Update the collection page to link out to all 5 blog posts
4. Publish all posts to Shopify via MCP

### Phase 4: Reporting
1. Generate summary report of all changes made
2. Before/after SEO scores per collection
3. List of all blog posts created with their target keywords
4. Internal linking map

---

## File Structure

```
shopify-seo-agent/
├── PLAN.md
├── README.md
├── pyproject.toml
├── .env.example
├── mcp_config.json                  # MCP server configurations
├── src/
│   ├── __init__.py
│   ├── main.py                      # CLI entrypoint & orchestrator
│   ├── config.py                    # Environment & settings
│   ├── mcp_servers/
│   │   ├── __init__.py
│   │   ├── shopify_server.py        # Shopify MCP server
│   │   ├── gsc_server.py            # Google Search Console MCP server
│   │   └── semrush_server.py        # SEMRush MCP server
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── collection_optimizer.py  # Collection page SEO optimizer
│   │   ├── keyword_researcher.py    # Keyword research & analysis
│   │   └── blog_generator.py        # Blog post content generator
│   ├── models/
│   │   ├── __init__.py
│   │   ├── collection.py            # Collection data models
│   │   ├── keyword.py               # Keyword data models
│   │   └── blog_post.py             # Blog post data models
│   └── utils/
│       ├── __init__.py
│       ├── seo_helpers.py           # SEO scoring & analysis utilities
│       └── linking.py               # Internal linking strategy builder
└── tests/
    ├── __init__.py
    ├── test_collection_optimizer.py
    ├── test_keyword_researcher.py
    └── test_blog_generator.py
```

---

## Technology Stack

- **Python 3.11+**
- **MCP SDK** (`mcp`) - Model Context Protocol client/server
- **httpx** - Async HTTP client for API calls
- **Pydantic** - Data validation and models
- **Click** - CLI interface
- **Rich** - Terminal output formatting
- **python-dotenv** - Environment variable management
