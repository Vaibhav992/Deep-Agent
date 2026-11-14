"""Eval metrics — correctness, latency, cost tracking."""
import time
from dataclasses import dataclass, field


@dataclass
class EvalResult:
    test_id: str
    category: str
    input_text: str
    expected: str
    actual: str
    score: float
    passed: bool
    latency_ms: float
    judge_reasoning: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class EvalSummary:
    total: int = 0
    passed: int = 0
    failed: int = 0
    avg_score: float = 0.0
    avg_latency_ms: float = 0.0
    by_category: dict = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def add(self, result: EvalResult):
        self.total += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
        self.avg_score = (
            (self.avg_score * (self.total - 1) + result.score) / self.total
        )
        self.avg_latency_ms = (
            (self.avg_latency_ms * (self.total - 1) + result.latency_ms) / self.total
        )
        cat = result.category
        if cat not in self.by_category:
            self.by_category[cat] = {"total": 0, "passed": 0, "avg_score": 0.0}
        c = self.by_category[cat]
        c["total"] += 1
        if result.passed:
            c["passed"] += 1
        c["avg_score"] = (c["avg_score"] * (c["total"] - 1) + result.score) / c["total"]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 3),
            "avg_score": round(self.avg_score, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "by_category": self.by_category,
        }
