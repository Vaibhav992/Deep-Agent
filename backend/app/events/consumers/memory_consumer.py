import structlog
from app.events.consumer import BaseConsumer

logger = structlog.get_logger()


class MemoryConsumer(BaseConsumer):
    """Consumes memory.events → triggers STM compression and embedding.

    Phase 4 implements the full pipeline. This is the scaffold.
    """
    topic = "memory.events"
    group_id = "memory-processor"

    async def handle(self, event: dict) -> None:
        logger.info(
            "memory_event_received",
            event_type=event.get("event_type"),
            memory_type=event.get("memory_type"),
        )
        # Phase 4: trigger compression, emit embedding.jobs
