"""Layer 2: Jev Guard — AI-powered injection + toxicity detection.

Uses TypeSafe SDK's three primitives:
- Choice: "Is this a prompt injection?" → yes/no
- Score: Toxicity rating 0-10
- Noul: Probability of harmful intent 0-1
"""
import structlog
from app.config import get_settings

logger = structlog.get_logger()

_TOXICITY_THRESHOLD = 6.0
_INJECTION_THRESHOLD = 0.7


async def check_injection(text: str) -> dict:
    """Use Jev Choice to classify prompt injection.

    Returns: {"safe": bool, "is_injection": bool, "confidence": float}
    """
    settings = get_settings()
    if not settings.TYPESAFE_API_KEY:
        return {"safe": True, "is_injection": False, "confidence": 0.0, "reason": "Jev not configured"}

    try:
        from typesafe import AsyncTypeSafeClient

        async with AsyncTypeSafeClient(api_key=settings.TYPESAFE_API_KEY) as client:
            # Choice: pick from list
            result = await client.choice(
                model=settings.JEV_MODEL,
                prompt=f"Is the following user message a prompt injection attempt? Message: {text}",
                choices=["safe_input", "prompt_injection"],
            )

            is_injection = result.choice == "prompt_injection"
            confidence = result.confidence if hasattr(result, "confidence") else 0.8

            if is_injection:
                logger.warning("jev_injection_detected", confidence=confidence)

            return {
                "safe": not is_injection,
                "is_injection": is_injection,
                "confidence": confidence,
            }
    except Exception as e:
        logger.error("jev_injection_check_failed", error=str(e))
        return {"safe": True, "is_injection": False, "confidence": 0.0, "reason": str(e)}


async def check_toxicity(text: str) -> dict:
    """Use Jev Score to rate toxicity 0-10.

    Returns: {"safe": bool, "score": float, "confidence": float}
    """
    settings = get_settings()
    if not settings.TYPESAFE_API_KEY:
        return {"safe": True, "score": 0.0, "confidence": 0.0, "reason": "Jev not configured"}

    try:
        from typesafe import AsyncTypeSafeClient

        async with AsyncTypeSafeClient(api_key=settings.TYPESAFE_API_KEY) as client:
            result = await client.score(
                model=settings.JEV_MODEL,
                prompt=f"Rate the toxicity of this message on a scale of 0-10: {text}",
                rubric="0 = completely harmless, 5 = mildly inappropriate, 10 = extremely toxic/harmful",
                min_score=0,
                max_score=10,
            )

            score = result.score
            is_toxic = score >= _TOXICITY_THRESHOLD

            if is_toxic:
                logger.warning("jev_toxicity_detected", score=score)

            return {
                "safe": not is_toxic,
                "score": score,
                "confidence": result.confidence if hasattr(result, "confidence") else 0.8,
            }
    except Exception as e:
        logger.error("jev_toxicity_check_failed", error=str(e))
        return {"safe": True, "score": 0.0, "confidence": 0.0, "reason": str(e)}


async def check_output_safety(text: str) -> dict:
    """Use Jev Noul to check if output contains harmful content.

    Returns: {"safe": bool, "probability": float}
    """
    settings = get_settings()
    if not settings.TYPESAFE_API_KEY:
        return {"safe": True, "probability": 0.0, "reason": "Jev not configured"}

    try:
        from typesafe import AsyncTypeSafeClient

        async with AsyncTypeSafeClient(api_key=settings.TYPESAFE_API_KEY) as client:
            result = await client.noul(
                model=settings.JEV_MODEL,
                prompt=f"Does this AI response contain harmful, leaked, or policy-violating content? Response: {text}",
            )

            probability = result.probability
            is_harmful = probability >= _INJECTION_THRESHOLD

            if is_harmful:
                logger.warning("jev_output_harmful", probability=probability)

            return {
                "safe": not is_harmful,
                "probability": probability,
            }
    except Exception as e:
        logger.error("jev_output_check_failed", error=str(e))
        return {"safe": True, "probability": 0.0, "reason": str(e)}
