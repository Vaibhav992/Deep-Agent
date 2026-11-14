"""Correctness judge — LLM evaluates if the answer is factually correct."""
from app.llm.factory import create_llm

JUDGE_PROMPT = """You are an evaluation judge. Given a question, an expected answer, and the actual answer produced by an AI agent, rate the correctness.

Question: {question}
Expected Answer: {expected}
Actual Answer: {actual}

Rate on a scale of 0.0 to 1.0:
- 1.0 = Fully correct, covers all key points
- 0.7 = Mostly correct, minor omissions
- 0.4 = Partially correct, significant gaps
- 0.0 = Incorrect or irrelevant

Respond in EXACTLY this format:
SCORE: <number>
REASONING: <one sentence explanation>"""


async def judge_correctness(question: str, expected: str, actual: str) -> tuple[float, str]:
    llm = create_llm(purpose="fast")
    response = await llm.ainvoke(
        JUDGE_PROMPT.format(question=question, expected=expected, actual=actual)
    )
    text = response.content
    score = 0.0
    reasoning = ""
    for line in text.strip().split("\n"):
        if line.startswith("SCORE:"):
            try:
                score = float(line.split(":", 1)[1].strip())
                score = max(0.0, min(1.0, score))
            except ValueError:
                score = 0.0
        elif line.startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()
    return score, reasoning
