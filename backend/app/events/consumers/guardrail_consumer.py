import structlog
from app.events.consumer import BaseConsumer

logger = structlog.get_logger()


class GuardrailAuditConsumer(BaseConsumer):
    """Consumes guardrail.events → writes to guardrail_log table.

    Phase 6 implements the full audit logging. This is the scaffold.
    """
    topic = "guardrail.events"
    group_id = "guardrail-auditor"

    async def handle(self, event: dict) -> None:
        logger.info(
            "guardrail_event_received",
            layer=event.get("layer"),
            decision=event.get("decision"),
        )
        # Phase 6: insert into guardrail_log table
