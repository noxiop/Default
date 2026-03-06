"""Main CLI entrypoint and orchestration pipeline for the SEO agent."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import click
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich.console import Console
from rich.table import Table

from src.agents.blog_generator import BlogGenerator
from src.agents.collection_optimizer import CollectionOptimizer
from src.agents.keyword_researcher import KeywordResearcher
from src.config import get_settings

console = Console()
logger = logging.getLogger("seo-agent")


# ---------------------------------------------------------------------------
# MCP Connection helpers
# ---------------------------------------------------------------------------

def _load_mcp_config() -> dict:
    config_path = Path("mcp_config.json")
    if not config_path.exists():
        raise FileNotFoundError("mcp_config.json not found in working directory")
    return json.loads(config_path.read_text())


def _server_params(config: dict, server_name: str) -> StdioServerParameters:
    srv = config["mcpServers"][server_name]
    return StdioServerParameters(
        command=srv["command"],
        args=srv.get("args", []),
        env=srv.get("env"),
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

async def run_pipeline(dry_run: bool = True, collections_filter: list[str] | None = None):
    """Run the full SEO optimization pipeline."""
    settings = get_settings()
    mcp_config = _load_mcp_config()

    console.print("\n[bold cyan]Shopify SEO Automation Agent[/bold cyan]")
    console.print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    console.print(f"Blog posts per collection: {settings.agent.blog_posts_per_collection}\n")

    # Connect to all 3 MCP servers
    console.print("[yellow]Connecting to MCP servers...[/yellow]")

    async with (
        stdio_client(_server_params(mcp_config, "shopify")) as (shopify_read, shopify_write),
        stdio_client(_server_params(mcp_config, "gsc")) as (gsc_read, gsc_write),
        stdio_client(_server_params(mcp_config, "semrush")) as (semrush_read, semrush_write),
    ):
        async with (
            ClientSession(shopify_read, shopify_write) as shopify_session,
            ClientSession(gsc_read, gsc_write) as gsc_session,
            ClientSession(semrush_read, semrush_write) as semrush_session,
        ):
            await shopify_session.initialize()
            await gsc_session.initialize()
            await semrush_session.initialize()
            console.print("[green]All MCP servers connected![/green]\n")

            site_domain = settings.gsc.site_url.replace("https://", "").replace("http://", "")

            # Initialize agents
            optimizer = CollectionOptimizer(shopify_session, site_domain)
            researcher = KeywordResearcher(semrush_session, gsc_session, site_domain)
            blog_gen = BlogGenerator(shopify_session, settings.gsc.site_url)

            # ---- Phase 1: Fetch collections ----
            console.print("[bold]Phase 1: Fetching collections[/bold]")
            collections = await optimizer.fetch_all_collections()

            if collections_filter:
                collections = [c for c in collections if c.handle in collections_filter]
                console.print(f"Filtered to {len(collections)} collections")

            collection_table = Table(title="Collections Found")
            collection_table.add_column("Handle")
            collection_table.add_column("Title")
            collection_table.add_column("Products")
            for c in collections:
                collection_table.add_row(c.handle, c.title, str(c.product_count))
            console.print(collection_table)

            # ---- Phase 2: Keyword research ----
            console.print("\n[bold]Phase 2: Keyword Research[/bold]")
            keyword_clusters = await researcher.research_all_collections(collections)

            kw_table = Table(title="Keyword Clusters")
            kw_table.add_column("Collection")
            kw_table.add_column("Primary Keyword")
            kw_table.add_column("Long-tail Count")
            for handle, cluster in keyword_clusters.items():
                kw_table.add_row(
                    handle,
                    cluster.primary_keyword.keyword,
                    str(len(cluster.long_tail_keywords)),
                )
            console.print(kw_table)

            # ---- Phase 3: Optimize collection pages ----
            console.print("\n[bold]Phase 3: Collection Page Optimization[/bold]")
            optimization_results = await optimizer.optimize_all(
                collections, keyword_clusters, dry_run
            )

            opt_table = Table(title="Optimization Results")
            opt_table.add_column("Collection")
            opt_table.add_column("Before Score")
            opt_table.add_column("Status")
            for r in optimization_results:
                status = "DRY RUN" if r["dry_run"] else "UPDATED"
                opt_table.add_row(r["collection"], str(r["before_score"]), status)
            console.print(opt_table)

            # ---- Phase 4: Generate & publish blog posts ----
            console.print("\n[bold]Phase 4: Blog Post Generation (Hub & Spoke)[/bold]")
            all_blog_results = []

            for collection in collections:
                cluster = keyword_clusters.get(collection.handle)
                if not cluster:
                    continue

                # Generate spoke posts
                posts = blog_gen.generate_spoke_posts(
                    collection,
                    cluster,
                    count=settings.agent.blog_posts_per_collection,
                )

                # Publish posts
                pub_results = await blog_gen.publish_blog_posts(posts, dry_run)
                all_blog_results.extend(pub_results)

                # Update hub with links to spokes
                await blog_gen.update_hub_with_spoke_links(collection, posts, dry_run)

            blog_table = Table(title="Blog Posts Generated")
            blog_table.add_column("Title")
            blog_table.add_column("Target Keyword")
            blog_table.add_column("Status")
            for r in all_blog_results:
                blog_table.add_row(r["title"], r["target_keyword"], r["status"])
            console.print(blog_table)

            # ---- Phase 5: Summary Report ----
            console.print("\n[bold]Phase 5: Summary Report[/bold]")
            report = {
                "timestamp": datetime.now().isoformat(),
                "mode": "dry_run" if dry_run else "live",
                "collections_processed": len(collections),
                "blog_posts_generated": len(all_blog_results),
                "optimization_results": optimization_results,
                "blog_results": all_blog_results,
            }

            report_path = Path("reports")
            report_path.mkdir(exist_ok=True)
            report_file = report_path / f"seo_report_{datetime.now():%Y%m%d_%H%M%S}.json"
            report_file.write_text(json.dumps(report, indent=2))
            console.print(f"\nReport saved to: {report_file}")

            console.print("\n[bold green]Pipeline complete![/bold green]")
            return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """Shopify SEO Automation Agent - Hub & Spoke Content Strategy"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


@cli.command()
@click.option("--live", is_flag=True, help="Run in live mode (applies changes)")
@click.option("--collection", "-c", multiple=True, help="Filter to specific collection handles")
def run(live: bool, collection: tuple[str, ...]):
    """Run the full SEO optimization pipeline."""
    dry_run = not live
    filter_list = list(collection) if collection else None
    asyncio.run(run_pipeline(dry_run=dry_run, collections_filter=filter_list))


@cli.command()
def status():
    """Show current configuration status."""
    settings = get_settings()
    console.print("\n[bold]Configuration Status[/bold]")
    console.print(f"  Shopify Store: {settings.shopify.store_url or '[red]NOT SET[/red]'}")
    console.print(f"  GSC Site:      {settings.gsc.site_url or '[red]NOT SET[/red]'}")
    console.print(f"  SEMRush Key:   {'[green]SET[/green]' if settings.semrush.api_key else '[red]NOT SET[/red]'}")
    console.print(f"  Dry Run:       {settings.agent.dry_run}")
    console.print(f"  Posts/Collection: {settings.agent.blog_posts_per_collection}")
    console.print()


if __name__ == "__main__":
    cli()
