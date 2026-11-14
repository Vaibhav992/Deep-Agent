"""LangGraph agent graph definition.

Flow:
    router → (research path) → planner → researcher (loop) → synthesizer → END
    router → (browse path)   → browser_agent → END
    router → (direct path)   → direct_answer → END

The researcher loops back to itself until all plan steps are done,
then routes to the synthesizer for the final answer.
"""
import functools
import time

from langgraph.graph import StateGraph, END

from app.agent.run_context import emit
from app.agent.state import AgentState
from app.agent.nodes.router import router_node
from app.agent.nodes.planner import planner_node
from app.agent.nodes.researcher import researcher_node
from app.agent.nodes.synthesizer import synthesizer_node
from app.agent.nodes.direct_answer import direct_answer_node
from app.agent.nodes.browser_agent import browser_agent_node


def _traced(name: str, fn):
    """Emit live node started/completed/failed events around a node."""
    @functools.wraps(fn)
    async def wrapper(state: AgentState):
        emit("node", {"node": name, "status": "started"})
        started = time.monotonic()
        try:
            result = await fn(state)
        except Exception:
            emit("node", {"node": name, "status": "failed", "duration_ms": round((time.monotonic() - started) * 1000)})
            raise
        emit("node", {"node": name, "status": "completed", "duration_ms": round((time.monotonic() - started) * 1000)})
        return result
    return wrapper


def _route_after_router(state: AgentState) -> str:
    return state.get("next_node", "direct_answer")


def _route_after_researcher(state: AgentState) -> str:
    return state.get("next_node", "synthesizer")


def build_graph() -> StateGraph:
    """Build and compile the agent graph."""
    graph = StateGraph(AgentState)

    graph.add_node("router", _traced("router", router_node))
    graph.add_node("planner", _traced("planner", planner_node))
    graph.add_node("researcher", _traced("researcher", researcher_node))
    graph.add_node("synthesizer", _traced("synthesizer", synthesizer_node))
    graph.add_node("direct_answer", _traced("direct_answer", direct_answer_node))
    graph.add_node("browser_agent", _traced("browser_agent", browser_agent_node))

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
