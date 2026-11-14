"""Agent state shared across all graph nodes.

LangGraph nodes read and write this TypedDict. The `messages` field
uses `add_messages` so each node appends to the conversation rather
than replacing it. Every other field is overwritten on each write.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # --- Core conversation ---
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str

    # --- Routing ---
    mode: str  # auto | research | browse | quick
    next_node: str
    from_node: str

    # --- Planner ---
    research_plan: list[str]
    current_step: int
    max_steps: int

    # --- Research context ---
    gathered_context: list[str]
    sources: list[dict[str, str]]

    # --- Model selection ---
    model_name: str | None
    purpose: str

    # --- Observability ---
    trace_id: str
    turn_start_time: float

    # --- Token/cost tracking for this turn ---
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
