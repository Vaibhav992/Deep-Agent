"""Guardrail Pipeline — orchestrates all 4 defense layers.

Fast-exit: if any layer blocks, skip the rest and return immediately.
This keeps latency low for the common case (safe input).
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

from app.security.heuristic_guard import check_input as heuristic_check_input, check_output as heuristic_check_output
from app.security.jev_guard import check_input as jev_check_input, check_output_safety
from app.security.llm_judge import check_high_risk

logger = structlog.get_logger()


class GuardrailDecision(Enum):
    SAFE = "safe"
    BLOCKED = "blocked"
    FLAGGED = "flagged"


@dataclass
class GuardrailResult:
    decision: GuardrailDecision
    layer: str
    confidence: float
    reason: str | None = None
    details: dict = field(default_factory=dict)


async def check_input(
    text: str,
    user_id: str,
    session_id: str,
    is_high_risk: bool = False,
) -> GuardrailResult:
    """Run input through layers 1-3. Fast-exit on block."""
    checks = []

    # Layer 1: Heuristic (free, instant)
    h_result = heuristic_check_input(text)
    checks.append(("heuristic", h_result))
    if not h_result["safe"]:
        result = GuardrailResult(
            decision=GuardrailDecision.BLOCKED,
            layer="heuristic",
            confidence=h_result["confidence"],
            reason=f"Matched injection pattern: {h_result['pattern']}",
        )
        await _log_all(user_id, session_id, "input", checks, result)
        return result

    # Layer 2: Jev injection + toxicity (one request)
    j_inject, j_toxic = await jev_check_input(text)
    checks.append(("jev_injection", j_inject))
    if not j_inject["safe"]:
        result = GuardrailResult(
            decision=GuardrailDecision.BLOCKED,
            layer="jev_injection",
            confidence=j_inject["confidence"],
            reason="Jev classified as prompt injection",
        )
        await _log_all(user_id, session_id, "input", checks, result)
        return result

    checks.append(("jev_toxicity", j_toxic))
    if not j_toxic["safe"]:
        result = GuardrailResult(
            decision=GuardrailDecision.BLOCKED,
            layer="jev_toxicity",
            confidence=j_toxic["confidence"],
            reason=f"Toxicity score: {j_toxic['score']}/10",
        )
        await _log_all(user_id, session_id, "input", checks, result)
        return result

    # Layer 3: LLM Judge (only for high-risk operations)
    if is_high_risk:
        llm_result = await check_high_risk(text)
        checks.append(("llm_judge", llm_result))
        if not llm_result["safe"]:
            result = GuardrailResult(
                decision=GuardrailDecision.BLOCKED,
                layer="llm_judge",
                confidence=llm_result["confidence"],
                reason=llm_result.get("reason", "LLM judge blocked"),
            )
            await _log_all(user_id, session_id, "input", checks, result)
            return result
        if llm_result.get("decision") == "flagged":
            result = GuardrailResult(
                decision=GuardrailDecision.FLAGGED,
                layer="llm_judge",
                confidence=llm_result["confidence"],
                reason=llm_result.get("reason"),
            )
            await _log_all(user_id, session_id, "input", checks, result)
            return result

    result = GuardrailResult(
        decision=GuardrailDecision.SAFE,
        layer="all",
        confidence=1.0,
    )
    await _log_all(user_id, session_id, "input", checks, result)
    return result


async def check_output(
    text: str,
    user_id: str,
    session_id: str,
) -> GuardrailResult:
    """Layer 4: validate agent output before sending to user."""
    checks = []

    # Heuristic output check (leaked prompts)
    h_result = heuristic_check_output(text)
    checks.append(("heuristic_output", h_result))
    if not h_result["safe"]:
        result = GuardrailResult(
            decision=GuardrailDecision.BLOCKED,
            layer="heuristic_output",
            confidence=h_result["confidence"],
            reason=f"Output contains system prompt fragment: {h_result['pattern']}",
        )
        await _log_all(user_id, session_id, "output", checks, result)
        return result

    # Jev output safety check
    j_output = await check_output_safety(text)
    checks.append(("jev_output", j_output))
    if not j_output["safe"]:
        result = GuardrailResult(
            decision=GuardrailDecision.BLOCKED,
            layer="jev_output",
            confidence=1.0 - j_output.get("probability", 0),
            reason="Jev flagged output as harmful",
        )
        await _log_all(user_id, session_id, "output", checks, result)
        return result

    return GuardrailResult(decision=GuardrailDecision.SAFE, layer="all", confidence=1.0)


async def _log_all(
    user_id: str,
    session_id: str,
    direction: str,
    checks: list[tuple[str, dict]],
    final: GuardrailResult,
):
    """Log all guardrail checks for audit trail."""
    logger.info(
        "guardrail_check",
        user_id=user_id,
        session_id=session_id,
        direction=direction,
        decision=final.decision.value,
        layer=final.layer,
        confidence=final.confidence,
        reason=final.reason,
        checks_run=len(checks),
    )
