"""Agent framework with tools and workflows."""

from .tools import create_knowledge_base_tool, create_web_search_tool
from .graph import create_agent
from .cross_examine import CrossExaminationTool

__all__ = [
    "create_knowledge_base_tool",
    "create_web_search_tool",
    "create_agent",
    "CrossExaminationTool"
]
