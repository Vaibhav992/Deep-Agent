"""Researcher node — executes one research step using tools."""
import time
import structlog

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage

from app.agent.state import AgentState
from app.agent.prompts.system import RESEARCHER_PROMPT
from app.llm.factory import create_llm
from app.tools.registry import get_research_tools

logger = structlog.get_logger()

_MAX_TOOL_ROUNDS = 5


async def researcher_node(state: AgentState) -> dict:
    """Execute the current research step, calling tools as needed."""
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

    tools = get_research_tools()
    tools_by_name = {t.name: t for t in tools}

   
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    for t in tools:
        if hasattr(t, "_user_id"):
            t._user_id = user_id
        if hasattr(t, "_session_id"):
            t._session_id = session_id

    llm = create_llm(state.get("model_name"), purpose="reasoning")
    llm_with_tools = llm.bind_tools(tools)

    messages = [SystemMessage(content=prompt), *state["messages"]]

  
    for _ in range(_MAX_TOOL_ROUNDS):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_fn = tools_by_name.get(tc["name"])
            if tool_fn is None:
                result = f"[Error] Unknown tool: {tc['name']}"
            else:
                try:
                    result = await tool_fn.ainvoke(tc["args"])
                except Exception as e:
                    logger.error("tool_call_failed", tool=tc["name"], error=str(e))
                    result = f"[Error] Tool {tc['name']} failed: {e}"
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    research_output = response.content.strip() if response.content else ""
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
