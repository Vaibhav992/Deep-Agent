"""Synthesizer node — combines all research into a final answer."""
import time
import structlog

from langchain_core.messages import SystemMessage, AIMessage

from app.agent.state import AgentState
from app.agent.prompts.system import SYNTHESIZER_PROMPT
from app.llm.factory import create_llm

logger = structlog.get_logger()


async def synthesizer_node(state: AgentState) -> dict:
    """Synthesize gathered research into a comprehensive answer."""
    start = time.monotonic()

    gathered = state.get("gathered_context", [])
    context_text = "\n\n".join(gathered) if gathered else "No research gathered."

    prompt = SYNTHESIZER_PROMPT.format(gathered_context=context_text)

    llm = create_llm(state.get("model_name"), purpose="reasoning")
    response = await llm.ainvoke([
        SystemMessage(content=prompt),
        *state["messages"],
    ])

    elapsed = (time.monotonic() - start) * 1000
    logger.info("synthesizer_complete", latency_ms=round(elapsed, 1))

    return {
        "messages": [AIMessage(content=response.content)],
        "from_node": "synthesizer",
    }
