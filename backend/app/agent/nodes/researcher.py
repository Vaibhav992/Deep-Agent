"""Researcher node: executes one plan step with research tools."""
import time

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.prompts.system import RESEARCHER_PROMPT
from app.agent.run_context import emit
from app.agent.state import AgentState
from app.agent.tooling import run_tool_calls
from app.llm.factory import create_llm
from app.tools.registry import get_research_tools

logger = structlog.get_logger()

MAX_TOOL_ROUNDS = 5


async def researcher_node(state: AgentState) -> dict:
    start = time.monotonic()
    current_step = state.get("current_step", 0)
    plan = state.get("research_plan", [])
    gathered = state.get("gathered_context", [])

    if current_step >= len(plan):
        return {"next_node": "synthesizer", "from_node": "researcher"}

    step_text = plan[current_step]
    emit("plan_step", {"index": current_step, "status": "running"})

    prompt = RESEARCHER_PROMPT.format(
        current_step=step_text,
        gathered_context="\n\n".join(gathered) if gathered else "None yet.",
    )
    tools = get_research_tools()
    tools_by_name = {t.name: t for t in tools}
    llm = create_llm(state.get("model_name"), purpose="agent")
    llm_with_tools = llm.bind_tools(tools)

    user_messages = [m for m in state["messages"] if not isinstance(m, AIMessage)]
    messages = [SystemMessage(content=prompt), *user_messages]

    research_output = ""
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)
            if not response.tool_calls:
                research_output = (response.content or "").strip()
                break
            messages.extend(await run_tool_calls(response, tools_by_name, node="researcher"))
        else:
            response = await llm.ainvoke([*messages, HumanMessage(
                content="Summarise what the tool results above established for this step. Note any gaps."
            )])
            research_output = (response.content or "").strip()
    except Exception:
        emit("plan_step", {"index": current_step, "status": "failed"})
        raise

    emit("plan_step", {"index": current_step, "status": "done"})
    new_step = current_step + 1
    next_node = "synthesizer" if new_step >= len(plan) else "researcher"
    logger.info("researcher_step_complete", step=new_step, total=len(plan), next=next_node,
                latency_ms=round((time.monotonic() - start) * 1000, 1))

    return {
        "gathered_context": gathered + [f"### Step {new_step}: {step_text}\n{research_output or '(no findings)'}"],
        "current_step": new_step,
        "next_node": next_node,
        "from_node": "researcher",
    }
