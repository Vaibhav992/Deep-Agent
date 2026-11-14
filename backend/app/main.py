from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.observability.logging_setup import setup_logging
from app.observability.middleware import RequestTracingMiddleware
from app.auth.middleware import ClerkAuthMiddleware

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("app_starting", env=settings.APP_ENV)

    from app.db.redis import redis_client
    from app.events.producer import KafkaProducer

    await KafkaProducer.get()

    # Auto-create tables in development (no Alembic needed for local Docker)
    if settings.APP_ENV == "development":
        from app.db.database import engine
        from app.db.base import Base
        # Import all models so Base.metadata knows about them
        import app.auth.models  # noqa: F401
        import app.sessions.models  # noqa: F401
        import app.chat.models  # noqa: F401
        import app.db.models  # noqa: F401
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("db_tables_created")

    logger.info("app_started")
    yield

    kafka = await KafkaProducer.get()
    await kafka.stop()
    try:
        await redis_client.close()
    except Exception:
        pass
    logger.info("app_stopped")


app = FastAPI(
    title="Deep Agent",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware order matters: CORS → Auth → Tracing (outermost applied last)
app.add_middleware(RequestTracingMiddleware)
app.add_middleware(ClerkAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# --- Routers ---
from app.auth.router import router as auth_router  # noqa: E402
from app.sessions.router import router as sessions_router  # noqa: E402
from app.chat.router import router as chat_router  # noqa: E402

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(chat_router)


@app.get("/health")
async def health():
    """Health check — also verifies DB and Redis connectivity."""
    checks = {"api": "ok"}
    try:
        from app.db.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        from app.db.redis import redis_client
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "env": settings.APP_ENV,
        "checks": checks,
    }


@app.get("/models", tags=["llm"])
async def list_models():
    from app.llm.factory import list_available_models
    return list_available_models()
