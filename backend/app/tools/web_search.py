"""Web search tool using Exa API.

Exa is a search engine built for AI — returns clean, structured
results with optional full-text content. Much better than scraping
Google results.
"""
import httpx
import structlog
from langchain_core.tools import tool

from app.config import get_settings

logger = structlog.get_logger()


@tool
async def web_search(query: str, num_results: int = 5) -> str:
    """Search the web for information on any topic.

    Use this when you need current information, facts, data, or
    research that may not be in your training data.

    Args:
        query: The search query. Be specific and descriptive.
        num_results: Number of results to return (1-10, default 5).

    Returns:
        Formatted search results with titles, URLs, and snippets.
    """
    settings = get_settings()
    if not settings.EXA_API_KEY:
        return "[Error] EXA_API_KEY not configured. Cannot perform web search."

    num_results = max(1, min(10, num_results))

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": settings.EXA_API_KEY},
                json={
                    "query": query,
                    "num_results": num_results,
                    "type": "auto",
                    "contents": {
                        "text": {"max_characters": 1500},
                        "highlights": {"num_sentences": 3},
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error("exa_search_failed", status=e.response.status_code)
            return f"[Error] Search failed with status {e.response.status_code}"
        except httpx.RequestError as e:
            logger.error("exa_search_error", error=str(e))
            return f"[Error] Search request failed: {e}"

    results = data.get("results", [])
    if not results:
        return f"No results found for: {query}"

    formatted = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        text = r.get("text", "")
        highlights = r.get("highlights", [])

        snippet = ""
        if highlights:
            snippet = " ".join(highlights[:2])
        elif text:
            snippet = text[:500]

        formatted.append(f"**{i}. {title}**\nURL: {url}\n{snippet}")

    return "\n\n".join(formatted)
