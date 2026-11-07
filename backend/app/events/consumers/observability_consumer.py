import structlog
from app.events.consumer import BaseConsumer

logger = structlog.get_logger()


class ObservabilityConsumer(BaseConsumer):
    """Consumes agent.events + session.events → forwards to LangFuse.

    Phase 7 implements the full forwarding. This is the scaffold.
    """
    topic = "agent.events"
    group_id = "observability-forwarder"

    async def handle(self, event: dict) -> None:
        logger.debug(
            "observability_event_received",
            event_type=event.get("event_type"),
            node=event.get("node_name"),
        )
        # Phase 7: forward to LangFuse via API
