"""Layer 1: Heuristic Guard — regex-based injection detection.

Cost: Free, ~0ms. Catches obvious prompt injection patterns.
"""
import re
import structlog

logger = structlog.get_logger()

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"system\s*prompt\s*:",
    r"<\|im_start\|>system",
    r"###\s*(system|instruction)",
    r"forget\s+(everything|all)",
    r"do\s+not\s+follow\s+(the|your)\s+(rules|instructions)",
    r"pretend\s+you\s+are",
    r"jailbreak",
    r"DAN\s+mode",
    r"ADMIN\s+OVERRIDE",
    r"base64\s+decode",
    r"eval\s*\(",
    r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions",
    r"override\s+(safety|content)\s+(filters?|policy)",
    r"reveal\s+(your|the)\s+(system|initial)\s+prompt",
    r"\bsudo\b.*\bmode\b",
]

_compiled = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

# Output patterns — detect leaked system prompts
OUTPUT_PATTERNS = [
    r"you\s+are\s+a\s+deep\s+research\s+agent",
    r"system\s+prompt\s*:",
    r"<\|im_start\|>",
    r"my\s+instructions\s+are",
    r"I\s+was\s+instructed\s+to",
]

_compiled_output = [re.compile(p, re.IGNORECASE) for p in OUTPUT_PATTERNS]


def check_input(text: str) -> dict:
    """Check input text for injection patterns.

    Returns: {"safe": bool, "pattern": str | None, "confidence": float}
    """
    for pattern in _compiled:
        match = pattern.search(text)
        if match:
            logger.warning("heuristic_injection_detected", pattern=match.group())
            return {
                "safe": False,
                "pattern": match.group(),
                "confidence": 0.9,
            }
    return {"safe": True, "pattern": None, "confidence": 1.0}


def check_output(text: str) -> dict:
    """Check output for leaked system prompts or PII patterns."""
    for pattern in _compiled_output:
        match = pattern.search(text)
        if match:
            logger.warning("heuristic_output_leak_detected", pattern=match.group())
            return {
                "safe": False,
                "pattern": match.group(),
                "confidence": 0.8,
            }
    return {"safe": True, "pattern": None, "confidence": 1.0}
