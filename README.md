# Shopify SEO Automation Agent

Automated SEO optimization agent that connects to **Shopify**, **Google Search Console**, and **SEMRush** via MCP (Model Context Protocol) to optimize collection pages and generate supporting blog content in a hub-and-spoke internal linking model.

## What It Does

1. **Fetches all Shopify collections** via the Shopify Admin GraphQL API
2. **Researches keywords** using GSC performance data + SEMRush keyword suggestions
3. **Optimizes collection pages** (meta titles, descriptions, body content)
4. **Generates 5 blog posts per collection** targeting long-tail keywords
5. **Builds internal links** in a hub-and-spoke model (collection = hub, blog posts = spokes)

## Architecture

```
SEO Agent Orchestrator
├── Shopify MCP Server   →  Shopify Admin GraphQL API
├── GSC MCP Server       →  Google Search Console API
└── SEMRush MCP Server   →  SEMRush API
```

Each MCP server runs as a separate stdio process, exposing tools that the agent orchestrator calls through the MCP client protocol.

## Setup

```bash
# 1. Clone and install
pip install -e ".[dev]"

# 2. Configure credentials
cp .env.example .env
# Edit .env with your API keys

# 3. Check configuration
seo-agent status

# 4. Run in dry-run mode (no changes applied)
seo-agent run

# 5. Run live (applies changes to Shopify)
seo-agent run --live

# 6. Filter to specific collections
seo-agent run -c "shoes" -c "shirts"
```

## Required API Credentials

| Service | What You Need | How to Get It |
|---------|--------------|---------------|
| Shopify | Admin API access token | Settings → Apps → Develop apps → Create app |
| GSC | Service account JSON key | Google Cloud Console → APIs → Search Console API |
| SEMRush | API key | SEMRush → API → Get API Key |

## MCP Server Configuration

The `mcp_config.json` defines the three MCP servers. Each server is launched as a subprocess and communicates via stdio:

```json
{
  "mcpServers": {
    "shopify": { "command": "python", "args": ["-m", "src.mcp_servers.shopify_server"] },
    "gsc":     { "command": "python", "args": ["-m", "src.mcp_servers.gsc_server"] },
    "semrush": { "command": "python", "args": ["-m", "src.mcp_servers.semrush_server"] }
  }
}
```

## Hub-and-Spoke Model

```
        Collection Page (HUB)
        /collections/shoes
               │
   ┌───┬───┬──┴──┬───┬───┐
   │   │   │     │   │   │
  Blog Blog Blog Blog Blog
   1    2    3    4    5
  (SPOKES)
```

- Each **spoke** blog post targets a long-tail keyword related to the collection
- Each spoke links **back to the hub** (collection page) with optimized anchor text
- Spokes **cross-link to each other** (1-2 links per post)
- The hub page is updated with **links to all spokes**

## Running Tests

```bash
pytest tests/ -v
```
