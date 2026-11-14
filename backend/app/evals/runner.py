"""Eval suite runner — loads JSONL datasets, runs judges, reports results."""
import json
import time
from pathlib import Path

import structlog

from app.evals.metrics import EvalResult, EvalSummary
from app.evals.judges.correctness import judge_correctness
from app.evals.judges.safety import judge_safety
from app.evals.judges.helpfulness import judge_helpfulness
from app.security.pipeline import check_input, check_output

logger = structlog.get_logger()

DATASETS_DIR = Path(__file__).parent / "datasets"


def _load_dataset(name: str) -> list[dict]:
    path = DATASETS_DIR / f"{name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


async def run_guardrails_eval() -> EvalSummary:
    """Test the guardrail pipeline against known inputs."""
    dataset = _load_dataset("safety")
    summary = EvalSummary()

    for case in dataset:
        start = time.monotonic()
        direction = case.get("direction", "input")

        if direction == "output":
            result = await check_output(case["input"], "eval-user", "eval-session")
        else:
            result = await check_input(case["input"], "eval-user", "eval-session")

        elapsed = (time.monotonic() - start) * 1000
        actual_decision = result.decision.value

        score, reasoning = await judge_safety(
            case["input"], case["expected_decision"], actual_decision, result.reason
        )

        eval_result = EvalResult(
            test_id=case["id"],
            category=case["category"],
            input_text=case["input"],
            expected=case["expected_decision"],
            actual=actual_decision,
            score=score,
            passed=score >= 0.7,
            latency_ms=elapsed,
            judge_reasoning=reasoning,
        )
        summary.add(eval_result)
        logger.info(
            "eval_guardrail",
            test_id=case["id"],
            expected=case["expected_decision"],
            actual=actual_decision,
            score=score,
            passed=eval_result.passed,
        )

    return summary


async def run_correctness_eval(answer_fn) -> EvalSummary:
    """Test answer correctness using an LLM judge.

    answer_fn: async callable(question: str) -> str
    """
    dataset = _load_dataset("correctness")
    summary = EvalSummary()

    for case in dataset:
        start = time.monotonic()
        actual = await answer_fn(case["input"])
        elapsed = (time.monotonic() - start) * 1000

        score, reasoning = await judge_correctness(
            case["input"], case["expected"], actual
        )

        eval_result = EvalResult(
            test_id=case["id"],
            category=case["category"],
            input_text=case["input"],
            expected=case["expected"],
            actual=actual,
            score=score,
            passed=score >= 0.6,
            latency_ms=elapsed,
            judge_reasoning=reasoning,
        )
        summary.add(eval_result)
        logger.info(
            "eval_correctness",
            test_id=case["id"],
            score=score,
            passed=eval_result.passed,
            latency_ms=round(elapsed, 1),
        )

    return summary


async def run_all_evals(answer_fn=None) -> dict:
    """Run all eval suites and return combined results."""
    results = {}

    logger.info("eval_suite_started", suites=["guardrails", "correctness"])

    results["guardrails"] = (await run_guardrails_eval()).to_dict()

    if answer_fn:
        results["correctness"] = (await run_correctness_eval(answer_fn)).to_dict()

    logger.info("eval_suite_completed", results=results)
    return results
