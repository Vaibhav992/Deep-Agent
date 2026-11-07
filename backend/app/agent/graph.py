"""LangGraph agent graph definition.

Flow:
    router → (research path) → planner → researcher (loop) → synthesizer → END
    router → (browse path)   → browser_agent → END
    router → (direct path)   → direct_answer → END

The researcher loops back to itself until all plan steps are done,
then routes to the synthesizer for the final answer.
"""
from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes.router import router_node
from app.agent.nodes.planner import planner_node
from app.agent.nodes.researcher import researcher_node
from app.agent.nodes.synthesizer import synthesizer_node
from app.agent.nodes.direct_answer import direct_answer_node
from app.agent.nodes.browser_agent import browser_agent_node


def _route_after_router(state: AgentState) -> str:
    return state.get("next_node", "direct_answer")


def _route_after_researcher(state: AgentState) -> str:
    return state.get("next_node", "synthesizer")


def build_graph() -> StateGraph:
    """Build and compile the agent graph."""
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("direct_answer", direct_answer_node)
    graph.add_node("browser_agent", browser_agent_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges("router", _route_after_router, {
        "planner": "planner",
        "browser_agent": "browser_agent",
        "direct_answer": "direct_answer",
    })

    graph.add_edge("planner", "researcher")

    graph.add_conditional_edges("researcher", _route_after_researcher, {
        "researcher": "researcher",
        "synthesizer": "synthesizer",
    })

    graph.add_edge("synthesizer", END)
    graph.add_edge("direct_answer", END)
    graph.add_edge("browser_agent", END)

    return graph.compile()


agent_graph = build_graph()
