from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

_meter: metrics.Meter | None = None


def get_meter() -> metrics.Meter:
    global _meter
    if _meter is None:
        reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=60000)
        provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(provider)
        _meter = metrics.get_meter("deep-agent")
    return _meter


meter = get_meter()

# Counters
requests_total = meter.create_counter("agent.requests.total")
tokens_used = meter.create_counter("agent.tokens.total")
cost_usd = meter.create_counter("agent.cost.usd")
guardrail_blocks = meter.create_counter("guardrail.blocks.total")

# Histograms
request_latency = meter.create_histogram("agent.request.latency_ms")
tool_latency = meter.create_histogram("agent.tool.latency_ms")


async def track_request(user_id: str, tokens: int, cost: float, latency: float):
    requests_total.add(1, {"user_id": user_id})
    tokens_used.add(tokens, {"user_id": user_id})
    cost_usd.add(cost, {"user_id": user_id})
    request_latency.record(latency, {"user_id": user_id})
