"""Main CLI entrypoint and orchestration pipeline for the SEO agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
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
        console.print(
            "\n[red]ERROR:[/red] mcp_config.json not found in working directory.\n"
            "  Make sure you are running from the project root directory.\n"
        )
        sys.exit(1)
    return json.loads(config_path.read_text())


def _interpolate_env(env_dict: dict[str, str] | None) -> dict[str, str] | None:
    """Replace ${VAR_NAME} placeholders with actual environment variable values."""
    if not env_dict:
        return env_dict
    result = {}
    for key, value in env_dict.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            result[key] = os.environ.get(var_name, "")
        else:
            result[key] = value
    return result


def _server_params(config: dict, server_name: str) -> StdioServerParameters:
    srv = config["mcpServers"][server_name]
    return StdioServerParameters(
        command=srv["command"],
        args=srv.get("args", []),
        env=_interpolate_env(srv.get("env")),
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

async def run_pipeline(dry_run: bool = True, collections_filter: list[str] | None = None):
    """Run the full SEO optimization pipeline."""
    settings = get_settings()

    # Validate credentials before doing anything
    problems = settings.validate_required()
    if problems:
        console.print("\n[red bold]Configuration problems found:[/red bold]")
        for i, problem in enumerate(problems, 1):
            console.print(f"  {i}. {problem}")
        console.print("\n  Edit your .env file to fix these, then try again.")
        console.print("  Run [cyan]python -m src.verify_setup[/cyan] for a full check.\n")
        sys.exit(1)

    mcp_config = _load_mcp_config()

    console.print("\n[bold cyan]Shopify SEO Automation Agent[/bold cyan]")
    console.print(f"Mode: {'[yellow]DRY RUN (no changes will be made)[/yellow]' if dry_run else '[red bold]LIVE (changes WILL be applied to Shopify)[/red bold]'}")
    console.print(f"Blog posts per collection: {settings.agent.blog_posts_per_collection}\n")

    if not dry_run:
        console.print("[yellow]You are in LIVE mode. Changes will be applied to your Shopify store.[/yellow]")
        console.print("[yellow]Press Ctrl+C within 5 seconds to cancel...[/yellow]")
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            console.print("\n[red]Cancelled.[/red]")
            return None

    # Connect to all 3 MCP servers
    console.print("[yellow]Connecting to MCP servers...[/yellow]")

    try:
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
                try:
                    collections = await optimizer.fetch_all_collections()
                except Exception as e:
                    console.print(f"\n[red]ERROR fetching collections from Shopify:[/red] {e}")
                    console.print("  Check that your SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN are correct.")
                    console.print("  Run [cyan]python -m src.verify_setup[/cyan] to test connectivity.\n")
                    sys.exit(1)

                if not collections:
                    console.print("[yellow]No collections found in your Shopify store.[/yellow]")
                    console.print("  Make sure your store has at least one collection.")
                    return None

                if collections_filter:
                    collections = [c for c in collections if c.handle in collections_filter]
                    if not collections:
                        console.print(f"[yellow]No collections matched your filter: {collections_filter}[/yellow]")
                        console.print("  Check the collection handles and try again.")
                        return None
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
                    status = "[yellow]DRY RUN[/yellow]" if r["dry_run"] else "[green]UPDATED[/green]"
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
                if dry_run:
                    console.print(
                        "\n[cyan]This was a dry run. No changes were made to your Shopify store.[/cyan]"
                        "\n[cyan]To apply changes for real, run: seo-agent run --live[/cyan]\n"
                    )
                return report

    except ConnectionRefusedError:
        console.print("\n[red]ERROR: Could not connect to MCP servers.[/red]")
        console.print("  The MCP servers are started automatically as subprocesses.")
        console.print("  Make sure the mcp package is installed: pip install -e '.[dev]'")
        console.print("  Run [cyan]python -m src.verify_setup[/cyan] for a full check.\n")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user.[/yellow]")
        return None


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
@click.option("--live", is_flag=True, help="Run in live mode (applies changes to Shopify)")
@click.option("--collection", "-c", multiple=True, help="Filter to specific collection handles")
def run(live: bool, collection: tuple[str, ...]):
    """Run the full SEO optimization pipeline.

    By default runs in DRY RUN mode (no changes are made).
    Use --live to actually apply changes to your Shopify store.
    """
    dry_run = not live
    filter_list = list(collection) if collection else None
    try:
        asyncio.run(run_pipeline(dry_run=dry_run, collections_filter=filter_list))
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")


@cli.command()
def status():
    """Show current configuration status and check for problems."""
    settings = get_settings()

    console.print("\n[bold]Configuration Status[/bold]")
    console.print(f"  Shopify Store:    {settings.shopify.store_url or '[red]NOT SET[/red]'}")
    console.print(f"  Shopify Token:    {'[green]SET[/green]' if settings.shopify.access_token else '[red]NOT SET[/red]'}")
    console.print(f"  Shopify Blog ID:  {settings.shopify.blog_id or '[red]NOT SET[/red]'}")
    console.print(f"  GSC Site:         {settings.gsc.site_url or '[red]NOT SET[/red]'}")
    console.print(f"  SEMRush Key:      {'[green]SET[/green]' if settings.semrush.api_key else '[red]NOT SET[/red]'}")
    console.print(f"  Dry Run:          {settings.agent.dry_run}")
    console.print(f"  Posts/Collection: {settings.agent.blog_posts_per_collection}")

    problems = settings.validate_required()
    if problems:
        console.print(f"\n[red bold]Issues found ({len(problems)}):[/red bold]")
        for i, p in enumerate(problems, 1):
            console.print(f"  {i}. {p}")
        console.print("\n  Edit your .env file to fix these issues.\n")
    else:
        console.print("\n[green]All required credentials are configured![/green]")
        console.print("  Run [cyan]seo-agent run[/cyan] to start a dry run.\n")


@cli.command()
def verify():
    """Run the full setup verification (checks packages, credentials, API connectivity)."""
    from src.verify_setup import run_verification
    run_verification()


if __name__ == "__main__":
    cli()
