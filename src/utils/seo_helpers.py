"""SEO analysis and scoring utilities."""

from __future__ import annotations

import re


def score_meta_title(title: str, primary_keyword: str) -> dict:
    """Score a meta title for SEO best practices."""
    issues = []
    length = len(title)

    if length == 0:
        issues.append("Missing meta title")
    elif length < 30:
        issues.append(f"Meta title too short ({length} chars, aim for 50-60)")
    elif length > 60:
        issues.append(f"Meta title too long ({length} chars, max 60)")

    keyword_lower = primary_keyword.lower()
    title_lower = title.lower()
    has_keyword = keyword_lower in title_lower
    keyword_front = title_lower.startswith(keyword_lower) if has_keyword else False

    if not has_keyword:
        issues.append("Primary keyword missing from meta title")
    elif not keyword_front:
        issues.append("Primary keyword not front-loaded in meta title")

    score = 100
    score -= len(issues) * 20

    return {
        "score": max(score, 0),
        "length": length,
        "has_keyword": has_keyword,
        "keyword_front_loaded": keyword_front,
        "issues": issues,
    }


def score_meta_description(description: str, primary_keyword: str) -> dict:
    """Score a meta description for SEO best practices."""
    issues = []
    length = len(description)

    if length == 0:
        issues.append("Missing meta description")
    elif length < 120:
        issues.append(f"Meta description too short ({length} chars, aim for 150-155)")
    elif length > 160:
        issues.append(f"Meta description too long ({length} chars, max 160)")

    has_keyword = primary_keyword.lower() in description.lower()
    if not has_keyword:
        issues.append("Primary keyword missing from meta description")

    has_cta = any(
        cta in description.lower()
        for cta in ["shop", "browse", "discover", "find", "explore", "get", "buy"]
    )
    if not has_cta:
        issues.append("No call-to-action found in meta description")

    score = 100 - len(issues) * 20
    return {
        "score": max(score, 0),
        "length": length,
        "has_keyword": has_keyword,
        "has_cta": has_cta,
        "issues": issues,
    }


def score_body_content(html: str, primary_keyword: str) -> dict:
    """Score body HTML content for basic SEO signals."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    word_count = len(text.split())

    issues = []
    if word_count < 50:
        issues.append(f"Content too thin ({word_count} words, aim for 150+)")

    keyword_lower = primary_keyword.lower()
    text_lower = text.lower()
    keyword_count = text_lower.count(keyword_lower)
    keyword_density = (keyword_count / max(word_count, 1)) * 100

    if keyword_count == 0:
        issues.append("Primary keyword not found in body content")
    elif keyword_density > 3.0:
        issues.append(f"Keyword density too high ({keyword_density:.1f}%, aim for 1-2%)")

    has_headings = bool(re.search(r"<h[2-3]", html, re.IGNORECASE))
    if word_count > 100 and not has_headings:
        issues.append("No H2/H3 subheadings found in content")

    score = 100 - len(issues) * 15
    return {
        "score": max(score, 0),
        "word_count": word_count,
        "keyword_count": keyword_count,
        "keyword_density": round(keyword_density, 2),
        "has_headings": has_headings,
        "issues": issues,
    }


def generate_meta_title(keyword: str, brand: str = "", max_length: int = 60) -> str:
    """Generate an SEO-optimized meta title."""
    if brand:
        title = f"{keyword.title()} | {brand}"
    else:
        title = keyword.title()

    if len(title) > max_length:
        title = title[:max_length - 3] + "..."
    return title


def generate_meta_description(
    keyword: str, context: str = "", max_length: int = 155
) -> str:
    """Generate an SEO-optimized meta description with CTA."""
    base = f"Explore our {keyword.lower()} collection"
    if context:
        base += f". {context}"
    base += ". Shop now and discover the best selection."

    if len(base) > max_length:
        base = base[:max_length - 3] + "..."
    return base
