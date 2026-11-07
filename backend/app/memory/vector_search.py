"""Hybrid search: pgvector cosine + BM25 keyword → Cohere Rerank.

The full RAG pipeline:
1. Vector search on child chunks → map to parent chunks
2. BM25 keyword search on recent archives
3. Merge + deduplicate
4. Cohere Rerank for final relevance scoring
"""
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from rank_bm25 import BM25Okapi
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentEmbedding, WorkingMemoryArchive
from app.memory.embeddings import embed_texts
from app.memory.reranker import rerank_results

logger = structlog.get_logger()


async def hybrid_search(
    db: AsyncSession,
    query: str,
    user_id: uuid.UUID,
    k: int = 5,
) -> list[str]:
    """Vector + BM25 → Cohere Rerank → top-k results."""

    # 1. Vector search: embed query → cosine similarity on child chunks
    query_emb = await embed_texts([query], input_type="search_query")
    child_results = (
        await db.execute(
            select(DocumentEmbedding)
            .where(
                and_(
                    DocumentEmbedding.user_id == user_id,
                    DocumentEmbedding.doc_type == "child",
                )
            )
            .order_by(DocumentEmbedding.embedding.cosine_distance(query_emb[0]))
            .limit(10)
        )
    ).scalars().all()

    # Map children to parent chunks (richer context)
    parent_ids = {r.parent_id for r in child_results if r.parent_id}
    parent_docs = []
    if parent_ids:
        parents = (
            await db.execute(
                select(DocumentEmbedding)
                .where(DocumentEmbedding.id.in_(parent_ids))
            )
        ).scalars().all()
        parent_docs = [p.content for p in parents]

    # 2. BM25 keyword search on recent archives (last 90 days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    archives = (
        await db.execute(
            select(WorkingMemoryArchive)
            .where(
                and_(
                    WorkingMemoryArchive.user_id == user_id,
                    WorkingMemoryArchive.date >= cutoff.date(),
                    WorkingMemoryArchive.summary.isnot(None),
                )
            )
        )
    ).scalars().all()

    bm25_docs = []
    if archives:
        archive_texts = [a.summary for a in archives]
        tokenized = [doc.lower().split() for doc in archive_texts]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(query.lower().split())
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        bm25_docs = [archive_texts[i] for i, score in ranked[:6] if score > 0]

    # 3. Merge + deduplicate
    all_docs = list(dict.fromkeys(parent_docs + bm25_docs))
    if not all_docs:
        return []

    # 4. Cohere Rerank
    reranked = await rerank_results(query, all_docs, top_n=k)
    return [r["text"] for r in reranked if r["score"] > 0.3]
