from dataclasses import dataclass


@dataclass(frozen=True)
class TopicConfig:
    name: str
    partitions: int
    retention_ms: int  # -1 = infinite


TOPICS = {
    "agent.events": TopicConfig("agent.events", partitions=6, retention_ms=7 * 86_400_000),
    "embedding.jobs": TopicConfig("embedding.jobs", partitions=3, retention_ms=3 * 86_400_000),
    "guardrail.events": TopicConfig("guardrail.events", partitions=3, retention_ms=30 * 86_400_000),
    "browser.events": TopicConfig("browser.events", partitions=3, retention_ms=7 * 86_400_000),
    "memory.events": TopicConfig("memory.events", partitions=3, retention_ms=3 * 86_400_000),
    "session.events": TopicConfig("session.events", partitions=3, retention_ms=7 * 86_400_000),
    "deadletter.events": TopicConfig("deadletter.events", partitions=1, retention_ms=-1),
}

# Convenience constants
AGENT_EVENTS = "agent.events"
EMBEDDING_JOBS = "embedding.jobs"
GUARDRAIL_EVENTS = "guardrail.events"
BROWSER_EVENTS = "browser.events"
MEMORY_EVENTS = "memory.events"
SESSION_EVENTS = "session.events"
DEADLETTER = "deadletter.events"
