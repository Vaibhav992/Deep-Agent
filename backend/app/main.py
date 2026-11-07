from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.observability.logging_setup import setup_logging
from app.observability.middleware import RequestTracingMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # Import here to avoid circular imports during module loading
    from app.db.redis import redis_client
    from app.events.producer import KafkaProducer

    await KafkaProducer.get()

    yield

    kafka = await KafkaProducer.get()
    await kafka.stop()
    await redis_client.close()


app = FastAPI(
    title="Deep Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTracingMiddleware)

# --- Routers ---
from app.auth.router import router as auth_router
from app.sessions.router import router as sessions_router
from app.chat.router import router as chat_router

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/models", tags=["llm"])
async def list_models():
    from app.llm.factory import list_available_models
    return list_available_models()
