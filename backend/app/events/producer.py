"""Singleton async Kafka producer.

Kafka is optional — when KAFKA_ENABLED=false (default), all emit()
calls silently no-op. This lets the app run without Kafka for local
dev and production on Render where we don't have a Kafka broker.

For local dev with Kafka: set KAFKA_ENABLED=true and run
docker-compose up kafka.
"""
import json

import structlog
from app.config import get_settings
from app.events.schemas import BaseEvent

logger = structlog.get_logger()


class KafkaProducer:
    _instance: "KafkaProducer | None" = None

    def __init__(self):
        self._producer = None
        self._started = False
        self._enabled = False

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
        if not settings.KAFKA_ENABLED:
            logger.info("kafka_disabled", reason="KAFKA_ENABLED=false")
            self._started = True
            return

        try:
            from aiokafka import AIOKafkaProducer
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
            self._enabled = True
            logger.info("kafka_producer_started", servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            logger.warning("kafka_producer_failed_to_start", error=str(e))
            self._producer = None
            self._started = True

    async def emit(self, topic: str, event: BaseEvent, key: str | None = None):
        if not self._enabled or not self._producer:
            return

        await self._producer.send_and_wait(
            topic=topic,
            value=event.model_dump(mode="json"),
            key=key,
        )
        logger.debug("kafka_event_emitted", topic=topic, event_type=event.event_type)

    async def stop(self):
        if self._producer and self._enabled:
            await self._producer.stop()
            self._enabled = False
            logger.info("kafka_producer_stopped")
        self._started = False

    @classmethod
    async def reset(cls):
        if cls._instance:
            await cls._instance.stop()
            cls._instance = None
