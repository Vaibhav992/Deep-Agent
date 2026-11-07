"""LLM provider registry.

Each provider is a (name → model_id) mapping. OpenRouter is special:
it proxies to many providers (DeepSeek, Meta, Mistral, etc.) via
a single API key and the OpenAI-compatible API format.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelInfo:
    model_id: str
    provider: str
    display_name: str
    context_window: int
    input_cost_per_1m: float  # USD per 1M input tokens
    output_cost_per_1m: float
    supports_vision: bool = False
    supports_tools: bool = True


# Provider catalogs — add models as needed, this is the source of truth
MODELS: dict[str, ModelInfo] = {
    # --- Gemini (direct via Google AI SDK) ---
    "gemini-2.5-pro": ModelInfo(
        model_id="gemini-2.5-pro",
        provider="gemini",
        display_name="Gemini 2.5 Pro",
        context_window=1_000_000,
        input_cost_per_1m=1.25,
        output_cost_per_1m=10.0,
        supports_vision=True,
    ),
    "gemini-2.5-flash": ModelInfo(
        model_id="gemini-2.5-flash",
        provider="gemini",
        display_name="Gemini 2.5 Flash",
        context_window=1_000_000,
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        supports_vision=True,
    ),

    # --- DeepSeek (direct API) ---
    "deepseek-chat": ModelInfo(
        model_id="deepseek-chat",
        provider="deepseek",
        display_name="DeepSeek V3",
        context_window=128_000,
        input_cost_per_1m=0.27,
        output_cost_per_1m=1.10,
    ),
    "deepseek-reasoner": ModelInfo(
        model_id="deepseek-reasoner",
        provider="deepseek",
        display_name="DeepSeek R1",
        context_window=128_000,
        input_cost_per_1m=0.55,
        output_cost_per_1m=2.19,
    ),

    # --- OpenRouter (proxy to any model) ---
    "openrouter/deepseek/deepseek-r1": ModelInfo(
        model_id="deepseek/deepseek-r1",
        provider="openrouter",
        display_name="DeepSeek R1 (via OpenRouter)",
        context_window=128_000,
        input_cost_per_1m=0.55,
        output_cost_per_1m=2.19,
    ),
    "openrouter/meta-llama/llama-4-maverick": ModelInfo(
        model_id="meta-llama/llama-4-maverick",
        provider="openrouter",
        display_name="Llama 4 Maverick (via OpenRouter)",
        context_window=1_000_000,
        input_cost_per_1m=0.20,
        output_cost_per_1m=0.60,
    ),
    "openrouter/mistralai/mistral-medium-3": ModelInfo(
        model_id="mistralai/mistral-medium-3",
        provider="openrouter",
        display_name="Mistral Medium 3 (via OpenRouter)",
        context_window=131_000,
        input_cost_per_1m=0.40,
        output_cost_per_1m=2.0,
    ),
    "openrouter/anthropic/claude-sonnet-4": ModelInfo(
        model_id="anthropic/claude-sonnet-4",
        provider="openrouter",
        display_name="Claude Sonnet 4 (via OpenRouter)",
        context_window=200_000,
        input_cost_per_1m=3.0,
        output_cost_per_1m=15.0,
        supports_vision=True,
    ),
}


# Purpose → default model mappings (user can override per-session or per-request)
PURPOSE_DEFAULTS: dict[str, str] = {
    "reasoning": "gemini-2.5-pro",
    "fast": "gemini-2.5-flash",
    "coding": "deepseek-chat",
    "vision": "gemini-2.5-pro",
    "fallback": "openrouter/meta-llama/llama-4-maverick",
}


def resolve_model(model_name: str | None, purpose: str = "fast") -> ModelInfo:
    """Resolve a model name (user input or purpose) to its ModelInfo.

    Priority:
    1. Exact match in MODELS registry
    2. Purpose-based default from PURPOSE_DEFAULTS
    3. Global default (gemini-2.5-flash)
    """
    if model_name and model_name in MODELS:
        return MODELS[model_name]

    default_key = PURPOSE_DEFAULTS.get(purpose, "gemini-2.5-flash")
    return MODELS.get(default_key, MODELS["gemini-2.5-flash"])
