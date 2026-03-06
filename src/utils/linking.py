"""Internal linking strategy builder for hub-and-spoke model."""

from __future__ import annotations

from src.models.blog_post import BlogPost, InternalLink


def build_hub_to_spoke_links(
    collection_handle: str,
    blog_posts: list[BlogPost],
    site_url: str = "",
) -> str:
    """Generate HTML for the hub page linking to all spoke blog posts.

    Returns an HTML section to append to the collection page body.
    """
    if not blog_posts:
        return ""

    lines = [
        '<div class="hub-spoke-links">',
        "<h2>Learn More</h2>",
        "<ul>",
    ]
    for post in blog_posts:
        url = f"{site_url}{post.url}" if site_url else post.url
        lines.append(f'  <li><a href="{url}">{post.title}</a></li>')
    lines.extend(["</ul>", "</div>"])
    return "\n".join(lines)


def build_spoke_to_hub_link(
    collection_handle: str,
    collection_title: str,
    site_url: str = "",
) -> InternalLink:
    """Create an internal link from a spoke blog post back to the hub collection."""
    url = f"{site_url}/collections/{collection_handle}"
    return InternalLink(
        url=url,
        anchor_text=collection_title,
        link_type="spoke_to_hub",
    )


def build_spoke_to_spoke_links(
    current_post: BlogPost,
    all_posts: list[BlogPost],
    max_links: int = 2,
    site_url: str = "",
) -> list[InternalLink]:
    """Create cross-links between spoke blog posts.

    Selects up to `max_links` other spoke posts for cross-linking.
    """
    other_posts = [p for p in all_posts if p.handle != current_post.handle]
    selected = other_posts[:max_links]
    links = []
    for post in selected:
        url = f"{site_url}{post.url}" if site_url else post.url
        links.append(
            InternalLink(
                url=url,
                anchor_text=post.title,
                link_type="spoke_to_spoke",
            )
        )
    return links


def inject_links_into_html(
    body_html: str,
    hub_link: InternalLink,
    spoke_links: list[InternalLink],
) -> str:
    """Inject internal links into blog post HTML content.

    Appends a related links section at the end of the content, and
    embeds the hub link naturally within the first paragraph.
    """
    # Embed hub link in the content (append after first paragraph)
    hub_tag = f'<a href="{hub_link.url}">{hub_link.anchor_text}</a>'
    first_p_end = body_html.find("</p>")
    if first_p_end > 0:
        insert_text = f" Browse our full <strong>{hub_tag}</strong> collection."
        body_html = body_html[:first_p_end] + insert_text + body_html[first_p_end:]

    # Append related posts section at the end
    if spoke_links:
        related = ["\n<hr>", '<div class="related-posts">', "<h3>Related Articles</h3>", "<ul>"]
        for link in spoke_links:
            related.append(f'  <li><a href="{link.url}">{link.anchor_text}</a></li>')
        related.extend(["</ul>", "</div>"])
        body_html += "\n".join(related)

    return body_html
