# Beginner Setup Guide - Step by Step

This guide walks you through setting up the Shopify SEO Agent from scratch. No prior experience needed.

---

## Prerequisites

You will need:
- A computer with **Python 3.11** or newer installed
- A **Shopify store** (with admin access)
- A **Google Search Console** account (with your store verified)
- A **SEMRush** account (free trial works for testing)

---

## Step 1: Install Python

Check if Python is installed by opening a terminal/command prompt and running:

```bash
python3 --version
```

You should see something like `Python 3.11.x` or higher. If not:
- **Mac**: `brew install python` (or download from python.org)
- **Windows**: Download from https://www.python.org/downloads/
- **Linux**: `sudo apt install python3.11 python3.11-venv`

---

## Step 2: Download and Install the Agent

```bash
# Navigate to the project folder
cd shopify-seo-agent

# Create a virtual environment (keeps things tidy)
python3 -m venv .venv

# Activate it
# Mac/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install the agent and its dependencies
pip install -e ".[dev]"
```

You should see packages installing. When it's done, verify:

```bash
seo-agent --help
```

You should see the help menu with available commands.

---

## Step 3: Get Your API Credentials

You need 3 sets of credentials. Here's how to get each one:

### 3a. Shopify Admin API Token

1. Log into your Shopify admin panel
2. Go to **Settings** (bottom left) > **Apps and sales channels**
3. Click **Develop apps** (top right)
4. Click **Create an app** > name it "SEO Agent"
5. Click **Configure Admin API scopes**
6. Enable these scopes:
   - `read_content` and `write_content` (for blog posts)
   - `read_products` (to see products in collections)
   - `read_online_store_pages` and `write_online_store_pages`
7. Click **Save** then **Install app**
8. Copy the **Admin API access token** (starts with `shpat_`)

Also note your **Blog ID**:
1. Go to **Online Store** > **Blog posts**
2. Click on your blog name (usually "News")
3. Look at the URL - it contains the blog ID number

### 3b. Google Search Console

**Option A - Simple (Access Token)**:
1. Go to https://search.google.com/search-console
2. Verify your Shopify store URL if not already done
3. Use the GSC API explorer to get a temporary access token
4. Set `GSC_ACCESS_TOKEN` in your .env

**Option B - Production (Service Account)**:
1. Go to https://console.cloud.google.com
2. Create a new project (or use an existing one)
3. Enable the "Search Console API"
4. Go to **Credentials** > **Create credentials** > **Service account**
5. Download the JSON key file
6. Save it as `credentials/gsc-service-account.json`
7. In Google Search Console, add the service account email as a user

### 3c. SEMRush API Key

1. Log into SEMRush
2. Go to your profile/subscription info
3. Find your API key (or request one if on a plan that includes it)
4. Copy the API key

---

## Step 4: Configure Your .env File

```bash
# Create your config file from the template
cp .env.example .env
```

Now open `.env` in any text editor and replace the placeholder values:

```env
# Replace these with YOUR real values:
SHOPIFY_STORE_URL=https://my-cool-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_abc123def456...
SHOPIFY_BLOG_ID=12345678

GSC_SITE_URL=https://my-cool-store.com
GSC_ACCESS_TOKEN=ya29.abc123...

SEMRUSH_API_KEY=abc123def456...

# Leave these as-is for now:
DRY_RUN=true
BLOG_POSTS_PER_COLLECTION=5
TARGET_BLOG_WORD_COUNT=1000
```

---

## Step 5: Verify Everything Works

Run the built-in verification tool:

```bash
python -m src.verify_setup
```

This checks:
- Python version
- All packages installed
- .env file exists
- All API keys are set (not placeholder values)
- Can actually connect to Shopify and SEMRush

Fix any issues it reports before continuing.

You can also run:
```bash
seo-agent status
```

---

## Step 6: Do a Dry Run (Safe - No Changes Made)

```bash
seo-agent run
```

This will:
1. Connect to your Shopify store and list all collections
2. Research keywords from GSC and SEMRush
3. Generate optimized titles, descriptions, and blog posts
4. Show you everything it WOULD change - but **makes no actual changes**

Review the output and the report file in `reports/`.

---

## Step 7: Run for Real (Apply Changes)

When you're happy with the dry run results:

```bash
seo-agent run --live
```

This will actually update your Shopify store. You'll get a 5-second countdown to cancel if needed.

**To run on just one collection first** (recommended):

```bash
seo-agent run --live -c "your-collection-handle"
```

---

## Step 8: Check Your Results

After running live:
1. Visit your Shopify admin > **Online Store** > **Blog posts** - you'll see the new posts
2. Check your collection pages - meta titles and descriptions are updated
3. Open the new blog posts - they link back to the collection page
4. The collection page links to all 5 blog posts

A JSON report is saved in `reports/` with all details.

---

## Troubleshooting

### "No module named 'mcp'" or similar
```bash
pip install -e ".[dev]"
```

### ".env file not found"
```bash
cp .env.example .env
# Then edit .env with your credentials
```

### "Shopify - invalid access token (401)"
- Double-check your `SHOPIFY_ACCESS_TOKEN` in `.env`
- Make sure the app is installed (not just created)
- Verify the API scopes are correct

### "No collections found"
- Your Shopify store needs at least one collection
- Create one in Shopify Admin > Products > Collections

### "Failed to get GSC data"
- GSC data can take a few days for new sites
- Make sure your site is verified in Search Console
- The agent will continue without GSC data (using SEMRush only)

### "SEMRush API error"
- Check your API key is correct
- Verify your SEMRush plan includes API access
- Free trials have limited API calls

---

## Running Tests

To verify the code itself works correctly:

```bash
pytest tests/ -v
```

This runs the unit tests that check the SEO scoring, keyword selection, and linking logic.
