"""Direct answer node — handles simple queries without research."""
import time
import structlog

from langchain_core.messages import SystemMessage, AIMessage

from app.agent.state import AgentState
from app.llm.factory import create_llm

logger = structlog.get_logger()

DIRECT_PROMPT = """\
You are a helpful AI assistant. Answer the user's question directly and concisely. \
Use markdown formatting when helpful."""


async def direct_answer_node(state: AgentState) -> dict:
    """Answer simple questions directly without the research pipeline."""
    start = time.monotonic()

    llm = create_llm(state.get("model_name"), purpose="fast")
    response = await llm.ainvoke([
        SystemMessage(content=DIRECT_PROMPT),
        *state["messages"],
    ])

    elapsed = (time.monotonic() - start) * 1000
    logger.info("direct_answer_complete", latency_ms=round(elapsed, 1))

    return {
        "messages": [AIMessage(content=response.content)],
        "from_node": "direct_answer",
    }
