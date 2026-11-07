import json
import asyncio

import structlog
from aiokafka import AIOKafkaConsumer

from app.config import get_settings

logger = structlog.get_logger()


class BaseConsumer:
    """Base class for Kafka consumers.

    Subclass, set `topic` and `group_id`, implement `handle()`.
    Failed events go to the dead letter topic for manual replay.
    """

    topic: str
    group_id: str

    def __init__(self):
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self):
        settings = get_settings()
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=self.group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await self._consumer.start()
        logger.info("kafka_consumer_started", topic=self.topic, group=self.group_id)

    async def handle(self, event: dict) -> None:
        raise NotImplementedError

    async def run(self):
        await self.start()
        try:
            async for msg in self._consumer:
                try:
                    await self.handle(msg.value)
                    await self._consumer.commit()
                except Exception as e:
                    logger.error(
                        "consumer_handle_error",
                        topic=self.topic,
                        error=str(e),
                        event_type=msg.value.get("event_type", "unknown"),
                    )
                    await self._send_to_deadletter(msg.value, str(e))
                    await self._consumer.commit()
        finally:
            if self._consumer:
                await self._consumer.stop()

    async def _send_to_deadletter(self, event: dict, error: str):
        from app.events.producer import KafkaProducer
        from app.events.schemas import BaseEvent
        from app.events.topics import DEADLETTER

        try:
            producer = await KafkaProducer.get()
            dead_event = BaseEvent(event_type="dead_letter")
            dead_event_data = dead_event.model_dump(mode="json")
            dead_event_data["_original_topic"] = self.topic
            dead_event_data["_original_event"] = event
            dead_event_data["_error"] = error
            await producer.emit(DEADLETTER, BaseEvent(event_type="dead_letter"))
        except Exception:
            logger.error("deadletter_send_failed", topic=self.topic)
