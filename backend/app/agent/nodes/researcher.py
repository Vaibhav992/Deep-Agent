"""Researcher node — executes one research step at a time."""
import time
import structlog

from langchain_core.messages import SystemMessage, AIMessage

from app.agent.state import AgentState
from app.agent.prompts.system import RESEARCHER_PROMPT
from app.llm.factory import create_llm

logger = structlog.get_logger()


async def researcher_node(state: AgentState) -> dict:
    """Execute the current research step and accumulate context."""
    start = time.monotonic()

    current_step = state.get("current_step", 0)
    plan = state.get("research_plan", [])
    gathered = state.get("gathered_context", [])

    if current_step >= len(plan):
        return {"next_node": "synthesizer", "from_node": "researcher"}

    step_text = plan[current_step]
    context_so_far = "\n\n".join(gathered) if gathered else "None yet."

    prompt = RESEARCHER_PROMPT.format(
        current_step=step_text,
        gathered_context=context_so_far,
    )

    llm = create_llm(state.get("model_name"), purpose="reasoning")
    response = await llm.ainvoke([
        SystemMessage(content=prompt),
        *state["messages"],
    ])

    research_output = response.content.strip()
    new_gathered = gathered + [f"### Step {current_step + 1}: {step_text}\n{research_output}"]
    new_step = current_step + 1

    if new_step >= len(plan):
        next_node = "synthesizer"
    else:
        next_node = "researcher"

    elapsed = (time.monotonic() - start) * 1000
    logger.info(
        "researcher_step_complete",
        step=current_step + 1,
        total=len(plan),
        next=next_node,
        latency_ms=round(elapsed, 1),
    )

    return {
        "gathered_context": new_gathered,
        "current_step": new_step,
        "next_node": next_node,
        "from_node": "researcher",
        "messages": [AIMessage(content=f"**Researching step {current_step + 1}/{len(plan)}:** {step_text}")],
    }
