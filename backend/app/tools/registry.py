"""Tool registry — central place to get all available tools.

Tools are registered here so the researcher node can bind them
to the LLM via `.bind_tools()`. Adding a new tool is just adding
it to the list below.
"""
from langchain_core.tools import BaseTool

from app.tools.think import think
from app.tools.web_search import web_search
from app.tools.read_url import read_url
from app.tools.memory_tools import search_memory, write_memory


def get_research_tools() -> list[BaseTool]:
    """Return all tools available for the research agent."""
    return [think, web_search, read_url, search_memory, write_memory]
