"""Helpfulness judge — rates how useful and well-structured the response is."""
from app.llm.factory import create_llm

JUDGE_PROMPT = """You are an evaluation judge. Rate how helpful this AI response is to the user's question.

Question: {question}
Response: {response}

Rate on a scale of 0.0 to 1.0:
- 1.0 = Excellent: comprehensive, well-structured, directly answers the question
- 0.7 = Good: answers the question but could be more detailed or better organized
- 0.4 = Fair: somewhat relevant but missing key information or poorly structured
- 0.0 = Unhelpful: doesn't answer the question, is generic, or is too short

Respond in EXACTLY this format:
SCORE: <number>
REASONING: <one sentence explanation>"""


async def judge_helpfulness(question: str, response: str) -> tuple[float, str]:
    llm = create_llm(purpose="fast")
    result = await llm.ainvoke(
        JUDGE_PROMPT.format(question=question, response=response)
    )
    text = result.content
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
