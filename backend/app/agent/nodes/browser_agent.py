"""Browser agent node — handles web browsing tasks via tools.

When the router detects a browsing intent (URL, "go to", "open website"),
it routes here. The browser agent has its own tool loop with browser-specific
tools (navigate, click, type, screenshot, etc.).
"""
import time
import structlog

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage

from app.agent.state import AgentState
from app.llm.factory import create_llm
from app.tools.browser.tools import get_browser_tools

logger = structlog.get_logger()

_MAX_BROWSER_ROUNDS = 10

BROWSER_AGENT_PROMPT = """\
You are a browser automation agent. You can navigate websites, click elements, \
fill forms, read page content, and take screenshots.

You are given a task to accomplish in the browser. Use the tools to:
1. Navigate to the right page
2. Read the accessibility tree to understand the page
3. Interact with elements by their index numbers
4. Extract the information needed

Rules:
- Always check the page structure after navigation or clicks
- Use element index numbers from the accessibility tree (marked with *)
- If an element isn't visible, try scrolling
- If a page is loading, use browser_wait
- Extract and summarize the information you find
- Report what you found when done"""


async def browser_agent_node(state: AgentState) -> dict:
    """Run the browser agent with its own tool loop."""
    start = time.monotonic()

    tools = get_browser_tools()
    tools_by_name = {t.name: t for t in tools}
    llm = create_llm(state.get("model_name"), purpose="reasoning")
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=BROWSER_AGENT_PROMPT),
        *state["messages"],
    ]

    for round_num in range(_MAX_BROWSER_ROUNDS):
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
                    logger.error("browser_tool_failed", tool=tc["name"], error=str(e))
                    result = f"[Error] {tc['name']} failed: {e}"
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        logger.info("browser_agent_round", round=round_num + 1, tool_calls=len(response.tool_calls))

    final_content = response.content.strip() if response.content else "Browser task completed."

    elapsed = (time.monotonic() - start) * 1000
    logger.info("browser_agent_complete", latency_ms=round(elapsed, 1))

    return {
        "next_node": "__end__",
        "from_node": "browser_agent",
        "messages": [AIMessage(content=final_content)],
    }
