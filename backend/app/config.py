from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    APP_SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: list[str] = ["http://localhost:3001", "http://localhost:5173"]

    # Database (Neon Postgres — cloud-hosted, no local postgres needed)
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/deepagent?sslmode=require"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth (Clerk)
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_JWKS_URL: str = "https://api.clerk.com/v1/jwks"

    # AI Guardrails (Jev via typesafe-sdk — SDK reads TYPESAFE_API_KEY from env)
    TYPESAFE_API_KEY: str = ""
    JEV_MODEL: str = "jev-latest"

    # LLM Providers
    GOOGLE_GENAI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Default LLM routing
    LLM_DEFAULT_PROVIDER: str = "gemini"
    LLM_DEFAULT_MODEL: str = "gemini-2.5-flash"
    LLM_REASONING_MODEL: str = "gemini-2.5-pro"
    LLM_FAST_MODEL: str = "gemini-2.5-flash"
    LLM_CODING_MODEL: str = "deepseek/deepseek-coder"

    # Embeddings & Re-ranking (Cohere)
    COHERE_API_KEY: str = ""

    # Search
    EXA_API_KEY: str = ""

    # Observability (LangFuse)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3000"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # Celery (periodic jobs only)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # Browser
    BROWSER_HEADLESS: bool = True
    BROWSER_SLOW_MO: int = 50
    BROWSER_TIMEOUT: int = 30000

    # Security
    RATE_LIMIT_PER_MINUTE: int = 30

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
