"""
LangGraph agent implementation with ReAct framework.

This module creates the agentic framework for academic inquiry
with memory, tool use, and multi-step reasoning.
"""

from typing import List, Optional, Any
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain.tools import Tool
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from llama_index.llms.google_genai import GoogleGenAI
from llama_index.llms.ollama import Ollama
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.core.indices.vector_store import VectorStoreIndex
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama

from .tools import (
    create_knowledge_base_tool,
    create_web_search_tool,
    create_file_reader_tool,
    create_list_projects_tool
)
from .cross_examine import create_cross_examine_tool
from ..integrations import create_zotero_tool, create_paper_finder_tool
from ..config import get_settings


def create_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1
):
    """
    Create an LLM client based on configuration.

    Args:
        provider: 'gemini' or 'ollama' (from settings if None)
        model: Model name (from settings if None)
        temperature: Sampling temperature

    Returns:
        LLM client instance
    """
    settings = get_settings()

    provider = provider or settings.default_llm_provider
    logger.info(f"Creating LLM client: {provider}")

    if provider == "gemini":
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY not configured")

        model = model or settings.gemini_model

        # Use LangChain's ChatGoogleGenerativeAI for agent compatibility
        # (LangGraph's create_react_agent needs a LangChain-compatible LLM)
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
            temperature=temperature
        )

        logger.success(f"Google GenAI LLM initialized: {model}")
        return llm

    elif provider == "ollama":
        model = model or settings.ollama_model

        llm = ChatOllama(
            model=model,
            base_url=settings.ollama_base_url,
            temperature=temperature
        )

        logger.success(f"Ollama LLM initialized: {model}")
        return llm

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def create_agent(
    query_engine: BaseQueryEngine,
    index: Optional[VectorStoreIndex] = None,
    pipeline: Optional[Any] = None,
    project_manager: Optional[Any] = None,
    llm: Optional[Any] = None,
    enable_memory: bool = True
):
    """
    Create a LangGraph ReAct agent with full tool suite.

    Args:
        query_engine: LlamaIndex query engine for knowledge base
        index: Optional VectorStoreIndex (for paper ingestion)
        pipeline: Optional DocumentPipeline (for paper ingestion)
        project_manager: Optional ProjectManager (for project tools)
        llm: Optional LLM client (created if None)
        enable_memory: Whether to enable conversation memory

    Returns:
        LangGraph agent executor
    """
    logger.info("Creating LangGraph ReAct agent")

    # Create LLM if not provided
    if llm is None:
        llm = create_llm()

    # Build tool list
    tools: List[Tool] = []

    # Core knowledge base tool
    kb_tool = create_knowledge_base_tool(query_engine)
    tools.append(kb_tool)
    logger.debug("Added knowledge base tool")

    # Web search tool
    web_tool = create_web_search_tool()
    if web_tool:
        tools.append(web_tool)
        logger.debug("Added web search tool")

    # File reader tool
    file_tool = create_file_reader_tool()
    tools.append(file_tool)
    logger.debug("Added file reader tool")

    # Cross-examination tool
    cross_exam_tool = create_cross_examine_tool(query_engine, llm)
    tools.append(cross_exam_tool)
    logger.debug("Added cross-examination tool")

    # Zotero tool
    zotero_tool = create_zotero_tool()
    if zotero_tool:
        tools.append(zotero_tool)
        logger.debug("Added Zotero tool")

    # Paper finder tool
    if index and pipeline:
        paper_tool = create_paper_finder_tool(pipeline, index)
        tools.append(paper_tool)
        logger.debug("Added paper finder tool")

    # Project management tool
    if project_manager:
        project_tool = create_list_projects_tool(project_manager)
        tools.append(project_tool)
        logger.debug("Added project management tool")

    logger.info(f"Agent configured with {len(tools)} tools")

    # Create memory saver if enabled
    checkpointer = MemorySaver() if enable_memory else None

    # Create agent
    agent = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer
    )

    logger.success("LangGraph agent created successfully")

    return agent


def create_agent_config(
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> dict:
    """
    Create configuration for agent execution.

    Args:
        thread_id: Conversation thread ID
        user_id: User ID

    Returns:
        Configuration dictionary
    """
    config = {
        "configurable": {
            "thread_id": thread_id or "default",
        }
    }

    if user_id:
        config["configurable"]["user_id"] = user_id

    return config


def format_agent_response(response: dict) -> str:
    """
    Format agent response for display.

    Args:
        response: Agent response dictionary

    Returns:
        Formatted response text
    """
    # Extract the final message
    messages = response.get("messages", [])

    if not messages:
        return "No response generated."

    # Get last assistant message
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'ai':
            return msg.content

    return str(messages[-1])


def stream_agent_response(agent, user_input: str, config: dict):
    """
    Stream agent response token by token.

    Args:
        agent: LangGraph agent
        user_input: User's input message
        config: Agent configuration

    Yields:
        Response chunks
    """
    logger.debug(f"Streaming agent response for: {user_input[:100]}...")

    try:
        # Create input
        inputs = {"messages": [("user", user_input)]}

        # Stream events
        for event in agent.stream(inputs, config, stream_mode="values"):
            # Get last message
            messages = event.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, 'content'):
                    yield last_msg.content

    except Exception as e:
        logger.error(f"Agent streaming failed: {e}")
        yield f"Error: {str(e)}"
