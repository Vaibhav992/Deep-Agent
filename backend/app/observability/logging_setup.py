import logging
import structlog
from app.config import get_settings


def setup_logging():
    settings = get_settings()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if settings.is_production
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Quiet noisy libraries. sse_starlette at DEBUG logs every chunk, including base64 screenshots.
    for noisy in ("httpx", "httpcore", "openai", "sse_starlette", "langfuse", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    logging.getLogger("aiokafka").setLevel(logging.INFO)
