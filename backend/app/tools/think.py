"""Think tool — structured reflection for the agent.

Gives the agent a scratchpad to reason through complex problems
before committing to an action. The output is added to context
but not shown to the user as a final answer.
"""
from langchain_core.tools import tool


@tool
def think(thought: str) -> str:
    """Use this tool to think through a problem step by step.

    Use it when you need to:
    - Break down a complex question before researching
    - Evaluate conflicting information
    - Plan your next research step
    - Reflect on what you've found so far

    Args:
        thought: Your reasoning, analysis, or plan. Be specific.

    Returns:
        The same thought, acknowledged. This is for YOUR reasoning,
        not shown as a final answer to the user.
    """
    return f"[Thought recorded] {thought}"
