"""Multi-provider LLM factory with automatic fallback.

Supports: Gemini (direct), DeepSeek (direct), OpenRouter (proxy),
OpenAI, Anthropic. Each provider uses the LangChain chat model
interface so the agent graph doesn't care which is active.
"""
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings
from app.llm.providers import ModelInfo, resolve_model, MODELS

settings = get_settings()


def _create_gemini(model_id: str) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=model_id,
        google_api_key=settings.GOOGLE_GENAI_API_KEY,
        temperature=0.7,
        convert_system_message_to_human=False,
    )


def _create_deepseek(model_id: str) -> BaseChatModel:
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model_id,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
        temperature=0.7,
    )


def _create_openrouter(model_id: str) -> BaseChatModel:
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model_id,
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.7,
        default_headers={"HTTP-Referer": "https://deep-agent.app"},
    )


def _create_openai(model_id: str) -> BaseChatModel:
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model_id,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
    )


def _create_anthropic(model_id: str) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=model_id,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.7,
    )


_PROVIDER_FACTORIES = {
    "gemini": _create_gemini,
    "deepseek": _create_deepseek,
    "openrouter": _create_openrouter,
    "openai": _create_openai,
    "anthropic": _create_anthropic,
}


def create_llm(
    model_name: str | None = None,
    purpose: str = "fast",
) -> BaseChatModel:
    """Create a chat model for the given model name or purpose.

    This is the single entry point for all LLM creation in the app.
    The agent graph, chat service, and tools all go through here.
    """
    info = resolve_model(model_name, purpose)
    factory = _PROVIDER_FACTORIES.get(info.provider)
    if not factory:
        raise ValueError(f"Unknown provider: {info.provider}")
    return factory(info.model_id)


def create_llm_with_fallback(
    model_name: str | None = None,
    purpose: str = "fast",
    fallback_purpose: str = "fallback",
) -> BaseChatModel:
    """Create a primary model with automatic fallback.

    Uses LangChain's .with_fallbacks() so a failed call
    transparently retries on the fallback model.
    """
    primary = create_llm(model_name, purpose)
    fallback = create_llm(purpose=fallback_purpose)
    return primary.with_fallbacks([fallback])


def list_available_models() -> list[dict]:
    """Return all registered models for the /models endpoint."""
    return [
        {
            "id": key,
            "display_name": info.display_name,
            "provider": info.provider,
            "context_window": info.context_window,
            "supports_vision": info.supports_vision,
            "supports_tools": info.supports_tools,
            "input_cost_per_1m": info.input_cost_per_1m,
            "output_cost_per_1m": info.output_cost_per_1m,
        }
        for key, info in MODELS.items()
    ]
