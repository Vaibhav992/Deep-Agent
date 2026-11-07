"""Cohere Embed v3 pipeline with local fallback.

Uses Cohere's embed-english-v3.0 (1024-dim) for production.
Falls back to local sentence-transformers if Cohere is unavailable.
"""
import uuid
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import DocumentEmbedding

logger = structlog.get_logger()

_local_model = None


async def embed_texts(
    texts: list[str],
    input_type: str = "search_document",
) -> list[list[float]]:
    """Embed texts via Cohere, fallback to local model."""
    settings = get_settings()

    if settings.COHERE_API_KEY:
        try:
            import cohere
            co = cohere.Client(api_key=settings.COHERE_API_KEY)
            response = co.embed(
                texts=texts,
                model="embed-english-v3.0",
                input_type=input_type,
                embedding_types=["float"],
            )
            return response.embeddings.float
        except Exception as e:
            logger.warning("cohere_embed_failed", error=str(e))

    return _embed_local(texts)


def _embed_local(texts: list[str]) -> list[list[float]]:
    """Fallback: local sentence-transformers (1024-dim to match Cohere)."""
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(
            "nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True
        )
    embeddings = _local_model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


async def embed_and_store(
    db: AsyncSession,
    user_id: uuid.UUID,
    content: str,
    source_type: str,
    source_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Embed a text and store it in the document_embeddings table.

    Uses parent-child chunking: splits into large parents, then
    smaller children. Searches match children, retrieves parents.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    parents = parent_splitter.split_text(content)
    batch_id = uuid.uuid4()

    for parent_text in parents:
        parent_emb = await embed_texts([parent_text], "search_document")
        parent = DocumentEmbedding(
            user_id=user_id,
            content=parent_text,
            embedding=parent_emb[0],
            doc_type="parent",
            source_type=source_type,
            source_id=source_id,
        )
        db.add(parent)
        await db.flush()

        children = child_splitter.split_text(parent_text)
        if children:
            child_embs = await embed_texts(children, "search_document")
            for child_text, child_emb in zip(children, child_embs):
                child = DocumentEmbedding(
                    user_id=user_id,
                    content=child_text,
                    embedding=child_emb,
                    doc_type="child",
                    source_type=source_type,
                    parent_id=parent.id,
                    source_id=source_id,
                )
                db.add(child)

    await db.commit()
    logger.info("embedded_document", user_id=str(user_id), source_type=source_type, parents=len(parents))
    return batch_id
