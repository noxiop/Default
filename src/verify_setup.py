"""Setup verification script.

Run this before using the agent to check that all API credentials
are configured correctly and the MCP servers can connect.

Usage:
    python -m src.verify_setup
    # or after installing:
    seo-agent verify
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Optional imports - we check if they're installed
_missing_packages: list[str] = []


def _check_package(name: str, import_name: str | None = None) -> bool:
    try:
        __import__(import_name or name)
        return True
    except ImportError:
        _missing_packages.append(name)
        return False


def _green(text: str) -> str:
    return f"\033[92m{text}\033[0m"


def _red(text: str) -> str:
    return f"\033[91m{text}\033[0m"


def _yellow(text: str) -> str:
    return f"\033[93m{text}\033[0m"


def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"


def check_python_version() -> bool:
    """Check that Python 3.11+ is being used."""
    v = sys.version_info
    if v.major == 3 and v.minor >= 11:
        print(f"  {_green('OK')} Python {v.major}.{v.minor}.{v.micro}")
        return True
    else:
        print(f"  {_red('FAIL')} Python {v.major}.{v.minor}.{v.micro} - need 3.11+")
        return False


def check_packages() -> bool:
    """Check that all required packages are installed."""
    packages = [
        ("mcp", "mcp"),
        ("httpx", "httpx"),
        ("pydantic", "pydantic"),
        ("click", "click"),
        ("rich", "rich"),
        ("python-dotenv", "dotenv"),
    ]
    all_ok = True
    for pip_name, import_name in packages:
        if _check_package(pip_name, import_name):
            print(f"  {_green('OK')} {pip_name}")
        else:
            print(f"  {_red('MISSING')} {pip_name}")
            all_ok = False

    if not all_ok:
        print(f"\n  {_yellow('FIX')}: Run: pip install -e \".[dev]\"")
    return all_ok


def check_env_file() -> bool:
    """Check that .env file exists."""
    if Path(".env").exists():
        print(f"  {_green('OK')} .env file found")
        return True
    else:
        print(f"  {_red('MISSING')} .env file not found")
        print(f"  {_yellow('FIX')}: Run: cp .env.example .env")
        print(f"        Then edit .env with your API credentials")
        return False


def check_env_vars() -> dict[str, bool]:
    """Check that required environment variables are set."""
    # Load .env if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    required = {
        "SHOPIFY_STORE_URL": "Shopify store URL (e.g., https://your-store.myshopify.com)",
        "SHOPIFY_ACCESS_TOKEN": "Shopify Admin API access token",
        "SHOPIFY_BLOG_ID": "Shopify blog ID for article creation",
        "GSC_SITE_URL": "Google Search Console site URL",
        "SEMRUSH_API_KEY": "SEMRush API key",
    }

    optional = {
        "GSC_CREDENTIALS_PATH": "Path to GSC service account JSON",
        "GSC_ACCESS_TOKEN": "GSC bearer token (alternative to credentials file)",
    }

    results = {}
    print()
    print(f"  {_bold('Required:')}")
    for var, description in required.items():
        value = os.environ.get(var, "")
        is_placeholder = value.startswith("your-") or "xxxxx" in value
        if value and not is_placeholder:
            # Mask the value for display
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print(f"  {_green('OK')} {var} = {masked}")
            results[var] = True
        elif is_placeholder:
            print(f"  {_red('PLACEHOLDER')} {var} - still has default value")
            print(f"       → {description}")
            results[var] = False
        else:
            print(f"  {_red('NOT SET')} {var}")
            print(f"       → {description}")
            results[var] = False

    print()
    print(f"  {_bold('Optional:')}")
    for var, description in optional.items():
        value = os.environ.get(var, "")
        if value:
            print(f"  {_green('OK')} {var}")
        else:
            print(f"  {_yellow('NOT SET')} {var} (optional)")

    return results


def check_mcp_config() -> bool:
    """Check that mcp_config.json exists and is valid."""
    config_path = Path("mcp_config.json")
    if not config_path.exists():
        print(f"  {_red('MISSING')} mcp_config.json not found")
        return False

    try:
        config = json.loads(config_path.read_text())
        servers = config.get("mcpServers", {})
        expected = ["shopify", "gsc", "semrush"]
        for name in expected:
            if name in servers:
                print(f"  {_green('OK')} MCP server '{name}' configured")
            else:
                print(f"  {_red('MISSING')} MCP server '{name}' not in config")
                return False
        return True
    except json.JSONDecodeError as e:
        print(f"  {_red('INVALID')} mcp_config.json has JSON errors: {e}")
        return False


async def check_shopify_connection() -> bool:
    """Test the Shopify API connection."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    store_url = os.environ.get("SHOPIFY_STORE_URL", "")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")

    if not store_url or not token:
        print(f"  {_yellow('SKIP')} Shopify - credentials not configured")
        return False

    try:
        import httpx
        url = f"{store_url}/admin/api/2024-01/graphql.json"
        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
        }
        query = '{"query": "{ shop { name } }"}'
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, headers=headers, content=query)
            if resp.status_code == 200:
                data = resp.json()
                shop_name = data.get("data", {}).get("shop", {}).get("name", "unknown")
                print(f"  {_green('OK')} Shopify connected - shop: {shop_name}")
                return True
            elif resp.status_code == 401:
                print(f"  {_red('FAIL')} Shopify - invalid access token (401)")
                print(f"       → Check your SHOPIFY_ACCESS_TOKEN in .env")
                return False
            else:
                print(f"  {_red('FAIL')} Shopify - HTTP {resp.status_code}")
                return False
    except Exception as e:
        print(f"  {_red('FAIL')} Shopify - {e}")
        return False


async def check_semrush_connection() -> bool:
    """Test the SEMRush API connection."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("SEMRUSH_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        print(f"  {_yellow('SKIP')} SEMRush - API key not configured")
        return False

    try:
        import httpx
        params = {
            "type": "domain_organic",
            "key": api_key,
            "domain": "example.com",
            "database": "us",
            "display_limit": 1,
            "export_columns": "Ph",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://api.semrush.com", params=params)
            text = resp.text.strip()
            if "ERROR" in text.upper():
                print(f"  {_red('FAIL')} SEMRush - API error: {text[:100]}")
                return False
            else:
                print(f"  {_green('OK')} SEMRush connected")
                return True
    except Exception as e:
        print(f"  {_red('FAIL')} SEMRush - {e}")
        return False


def run_verification():
    """Run all verification checks."""
    print()
    print(_bold("=" * 55))
    print(_bold("  Shopify SEO Agent - Setup Verification"))
    print(_bold("=" * 55))

    all_passed = True

    # 1. Python version
    print(f"\n{_bold('1. Python Version')}")
    if not check_python_version():
        all_passed = False

    # 2. Required packages
    print(f"\n{_bold('2. Required Packages')}")
    if not check_packages():
        all_passed = False

    # 3. .env file
    print(f"\n{_bold('3. Environment File')}")
    if not check_env_file():
        all_passed = False

    # 4. Environment variables
    print(f"\n{_bold('4. API Credentials')}")
    env_results = check_env_vars()
    if not all(env_results.values()):
        all_passed = False

    # 5. MCP config
    print(f"\n{_bold('5. MCP Configuration')}")
    if not check_mcp_config():
        all_passed = False

    # 6. API connectivity
    print(f"\n{_bold('6. API Connectivity (live checks)')}")
    try:
        shopify_ok = asyncio.run(check_shopify_connection())
        semrush_ok = asyncio.run(check_semrush_connection())
    except Exception:
        shopify_ok = False
        semrush_ok = False
    if not (shopify_ok and semrush_ok):
        # Not a hard failure - they may not have credentials yet
        pass

    # Summary
    print()
    print(_bold("=" * 55))
    if all_passed:
        print(f"  {_green('ALL CHECKS PASSED')} - You're ready to run the agent!")
        print(f"  Start with: seo-agent run  (dry run, safe mode)")
    else:
        print(f"  {_yellow('SOME CHECKS NEED ATTENTION')}")
        print(f"  Fix the issues above, then run this again:")
        print(f"  python -m src.verify_setup")
    print(_bold("=" * 55))
    print()

    return all_passed


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
