"""Read URL tool — fetches and extracts text from a web page.

Uses httpx + BeautifulSoup to fetch a page and extract the main
text content, stripping navigation, ads, scripts, etc.
"""
import httpx
import structlog
from langchain_core.tools import tool

from app.security.url_policy import UrlPolicyError, check_url

logger = structlog.get_logger()

_UNWANTED_TAGS = {"script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"}
_MAX_CONTENT_LENGTH = 8000


@tool
async def read_url(url: str) -> str:
    """Read and extract the main text content from a web page.

    Use this when you have a specific URL and need to read its content.
    Works best on articles, documentation, and blog posts.

    Args:
        url: The full URL to read (must start with http:// or https://).

    Returns:
        The extracted text content from the page.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DeepAgent/1.0; +https://deep-agent.app)",
        "Accept": "text/html,application/xhtml+xml",
    }

    # Follow redirects by hand so every hop is checked against the URL policy.
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        try:
            for _ in range(6):
                try:
                    url = await check_url(url)
                except UrlPolicyError as e:
                    return f"[Blocked] {e}"
                response = await client.get(url, headers=headers)
                if response.is_redirect and response.headers.get("location"):
                    url = str(response.url.join(response.headers["location"]))
                    continue
                break
            else:
                return f"[Error] Too many redirects fetching {url}"
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            return f"[Error] HTTP {e.response.status_code} fetching {url}"
        except httpx.RequestError as e:
            return f"[Error] Failed to fetch URL: {e}"

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        return f"[Error] URL returned non-HTML content type: {content_type}"

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.find_all(_UNWANTED_TAGS):
            tag.decompose()

        # Try to find main content area
        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find(role="main")
            or soup.find("div", class_="content")
            or soup.body
        )

        if not main:
            return "[Error] Could not extract content from page."

        text = main.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        if len(text) > _MAX_CONTENT_LENGTH:
            text = text[:_MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"

        title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"

        return f"**{title}**\nSource: {url}\n\n{text}"

    except Exception as e:
        logger.error("read_url_parse_error", url=url, error=str(e))
        return f"[Error] Failed to parse page content: {e}"
