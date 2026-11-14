"""Regression tests for the agent runtime: tool events, run context, page snapshots, titles."""
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

import app.agent.tooling as tooling
from app.agent.run_context import RunContext, current_run, reset_current_run, set_current_run
from app.browser.accessibility import format_tree_for_agent
from app.chat.service import _title_from


@tool
async def echo(text: str) -> str:
    """Echo text back."""
    return f"echo: {text}"


@tool
async def boom() -> str:
    """Always fails."""
    raise RuntimeError("kaboom")


async def test_run_tool_calls_emits_start_and_end_with_ids(monkeypatch):
    events = []
    monkeypatch.setattr(tooling, "emit", lambda name, data: events.append((name, data)))
    token = set_current_run(RunContext(run_id="r1", user_id="u1", session_id="s1"))
    try:
        response = AIMessage(content="", tool_calls=[
            {"name": "echo", "args": {"text": "hi"}, "id": "call_1"},
            {"name": "boom", "args": {}, "id": "call_2"},
            {"name": "missing", "args": {}, "id": "call_3"},
        ])
        msgs = await tooling.run_tool_calls(response, {"echo": echo, "boom": boom}, node="researcher")
        assert current_run().tool_calls == 3
    finally:
        reset_current_run(token)

    assert [m.tool_call_id for m in msgs] == ["call_1", "call_2", "call_3"]
    assert msgs[0].content == "echo: hi"
    assert msgs[1].content.startswith("[Error] boom failed")
    assert msgs[2].content.startswith("[Error] Unknown tool")

    names = [e[0] for e in events]
    assert names == ["tool_start", "tool_end"] * 3
    ends = [d for n, d in events if n == "tool_end"]
    assert [e["ok"] for e in ends] == [True, False, False]
    assert all(isinstance(e["duration_ms"], int) for e in ends)


async def test_current_call_id_visible_inside_tool_and_reset_after(monkeypatch):
    seen = {}

    @tool
    async def probe() -> str:
        """Record the current call id."""
        seen["id"] = tooling.current_call_id.get()
        return "ok"

    monkeypatch.setattr(tooling, "emit", lambda *a: None)
    token = set_current_run(RunContext(run_id="r", user_id="u", session_id="s"))
    try:
        await tooling.run_tool_calls(AIMessage(content="", tool_calls=[{"name": "probe", "args": {}, "id": "c9"}]),
                                     {"probe": probe}, node="browser_agent")
    finally:
        reset_current_run(token)
    assert seen["id"] == "c9"
    assert tooling.current_call_id.get() is None


def test_snapshot_marks_interactive_and_offscreen():
    tree = [
        {"index": 0, "role": "heading 1", "name": "Example Domain", "interactive": False, "in_viewport": True},
        {"index": 1, "role": "link", "name": "More information", "interactive": True, "in_viewport": False},
    ]
    text = format_tree_for_agent(tree)
    assert "[0]  heading 1: Example Domain" in text
    assert "[1]* link: More information (off-screen)" in text
    assert "1 interactive" in text


def test_empty_snapshot_gives_actionable_hint():
    assert "browser_wait" in format_tree_for_agent([])


def test_title_from_collapses_whitespace_and_truncates():
    assert _title_from("  Compare   React\nand Vue  ") == "Compare React and Vue"
    long = "word " * 40
    title = _title_from(long)
    assert len(title) <= 60 and title.endswith("…")
