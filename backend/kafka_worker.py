"""Kafka consumer worker — runs all consumer groups concurrently.

Start: python -m kafka_worker
Docker: the kafka_worker service in docker-compose runs this.
"""
import asyncio
import structlog

from app.observability.logging_setup import setup_logging
from app.events.consumers.embedding_consumer import EmbeddingConsumer
from app.events.consumers.guardrail_consumer import GuardrailAuditConsumer
from app.events.consumers.observability_consumer import ObservabilityConsumer
from app.events.consumers.memory_consumer import MemoryConsumer

logger = structlog.get_logger()


async def main():
    setup_logging()
    logger.info("kafka_worker_starting")

    consumers = [
        EmbeddingConsumer(),
        GuardrailAuditConsumer(),
        ObservabilityConsumer(),
        MemoryConsumer(),
    ]

    logger.info("kafka_worker_running", consumers=len(consumers))
    await asyncio.gather(*(c.run() for c in consumers))


if __name__ == "__main__":
    asyncio.run(main())
