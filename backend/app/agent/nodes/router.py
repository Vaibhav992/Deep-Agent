"""Router node — decides if a query needs deep research or a direct answer."""
import time
import structlog

from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.state import AgentState
from app.agent.prompts.system import ROUTER_PROMPT
from app.llm.factory import create_llm

logger = structlog.get_logger()

_FORCED_MODES = {"research": "planner", "browse": "browser_agent", "quick": "direct_answer"}


async def router_node(state: AgentState) -> dict:
    """Classify the user's intent: research or direct answer."""
    start = time.monotonic()

    forced = _FORCED_MODES.get(state.get("mode") or "auto")
    if forced:
        logger.info("router_decision", decision=forced, forced=True)
        return {"next_node": forced, "from_node": "router"}

    last_message = state["messages"][-1]
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    llm = create_llm(state.get("model_name"), purpose="fast")
    response = await llm.ainvoke([
        SystemMessage(content=ROUTER_PROMPT.format(message=user_text)),
        HumanMessage(content=user_text),
    ])

    decision = response.content.strip().lower()
    if "research" in decision:
        next_node = "planner"
    elif "browse" in decision:
        next_node = "browser_agent"
    else:
        next_node = "direct_answer"

    elapsed = (time.monotonic() - start) * 1000
    logger.info("router_decision", decision=next_node, latency_ms=round(elapsed, 1))

    return {
        "next_node": next_node,
        "from_node": "router",
    }
