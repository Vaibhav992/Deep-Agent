"""Planner node — breaks a research query into steps."""
import time
import structlog

from langchain_core.messages import SystemMessage, AIMessage

from app.agent.state import AgentState
from app.agent.prompts.system import PLANNER_PROMPT
from app.llm.factory import create_llm

logger = structlog.get_logger()


async def planner_node(state: AgentState) -> dict:
    """Generate a research plan from the user's question."""
    start = time.monotonic()

    llm = create_llm(state.get("model_name"), purpose="reasoning")
    response = await llm.ainvoke([
        SystemMessage(content=PLANNER_PROMPT),
        *state["messages"],
    ])

    plan_text = response.content.strip()
    steps = [
        line.strip().lstrip("0123456789.").strip()
        for line in plan_text.split("\n")
        if line.strip() and line.strip()[0].isdigit()
    ]

    if not steps:
        steps = [plan_text]

    elapsed = (time.monotonic() - start) * 1000
    logger.info("planner_complete", steps=len(steps), latency_ms=round(elapsed, 1))

    return {
        "research_plan": steps,
        "current_step": 0,
        "max_steps": len(steps),
        "gathered_context": [],
        "sources": [],
        "from_node": "planner",
        "messages": [AIMessage(content=f"**Research Plan:**\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)))],
    }
