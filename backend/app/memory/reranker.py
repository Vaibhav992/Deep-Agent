"""Cohere Rerank v3.5 — re-scores retrieved documents by relevance."""
import structlog
from app.config import get_settings

logger = structlog.get_logger()


async def rerank_results(
    query: str,
    documents: list[str],
    top_n: int = 5,
) -> list[dict]:
    """Re-rank documents using Cohere Rerank for better relevance.

    Returns list of {"text": str, "score": float, "index": int}.
    Falls back to returning documents as-is if Cohere is unavailable.
    """
    if not documents:
        return []

    settings = get_settings()
    if settings.COHERE_API_KEY:
        try:
            import cohere
            co = cohere.Client(api_key=settings.COHERE_API_KEY)
            response = co.rerank(
                query=query,
                documents=documents,
                model="rerank-english-v3.5",
                top_n=min(top_n, len(documents)),
            )
            return [
                {"text": documents[r.index], "score": r.relevance_score, "index": r.index}
                for r in response.results
            ]
        except Exception as e:
            logger.warning("cohere_rerank_failed", error=str(e))

    return [{"text": doc, "score": 1.0, "index": i} for i, doc in enumerate(documents[:top_n])]
