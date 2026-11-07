import json

import structlog
from aiokafka import AIOKafkaProducer

from app.config import get_settings
from app.events.schemas import BaseEvent

logger = structlog.get_logger()


class KafkaProducer:
    """Singleton async Kafka producer.

    Idempotent writes (acks=all, enable_idempotence) guarantee
    exactly-once delivery to the broker. Linger batches small
    events for throughput without blocking the caller.
    """

    _instance: "KafkaProducer | None" = None

    def __init__(self):
        self._producer: AIOKafkaProducer | None = None
        self._started = False

    @classmethod
    async def get(cls) -> "KafkaProducer":
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.start()
        return cls._instance

    async def start(self):
        if self._started:
            return
        settings = get_settings()
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                enable_idempotence=True,
                max_batch_size=32768,
                linger_ms=10,
            )
            await self._producer.start()
            self._started = True
            logger.info("kafka_producer_started")
        except Exception as e:
            logger.warning("kafka_producer_failed_to_start", error=str(e))
            self._producer = None

    async def emit(self, topic: str, event: BaseEvent, key: str | None = None):
        if not self._producer:
            logger.debug("kafka_skip_emit_no_producer", topic=topic)
            return

        await self._producer.send_and_wait(
            topic=topic,
            value=event.model_dump(mode="json"),
            key=key,
        )
        logger.debug("kafka_event_emitted", topic=topic, event_type=event.event_type)

    async def stop(self):
        if self._producer and self._started:
            await self._producer.stop()
            self._started = False
            logger.info("kafka_producer_stopped")

    @classmethod
    async def reset(cls):
        """For testing: tear down the singleton."""
        if cls._instance:
            await cls._instance.stop()
            cls._instance = None
