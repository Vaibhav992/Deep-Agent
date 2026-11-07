import structlog
from app.events.consumer import BaseConsumer

logger = structlog.get_logger()


class EmbeddingConsumer(BaseConsumer):
    """Consumes embedding.jobs → runs Cohere embed → upserts to pgvector.

    Phase 4 implements the full pipeline. This is the scaffold.
    """
    topic = "embedding.jobs"
    group_id = "embedding-worker"

    async def handle(self, event: dict) -> None:
        logger.info(
            "embedding_job_received",
            source_id=event.get("source_id"),
            chunks=len(event.get("text_chunks", [])),
        )
        # Phase 4: embed_texts() + pgvector upsert
