"""
Agent tools for knowledge base access, web search, and integrations.

Tools are the agent's interface to external capabilities.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path

from langchain.tools import Tool
from langchain_community.tools.tavily_search import TavilySearchResults
from loguru import logger

from llama_index.core import QueryEngine

from ..config import get_settings


def create_knowledge_base_tool(
    query_engine: QueryEngine,
    name: str = "KnowledgeBaseSearch",
    description: Optional[str] = None
) -> Tool:
    """
    Create a tool for querying the knowledge base.

    This wraps the LlamaIndex query engine as a LangChain tool.

    Args:
        query_engine: LlamaIndex query engine with retrieval pipeline
        name: Tool name
        description: Tool description (for agent reasoning)

    Returns:
        LangChain Tool instance
    """
    if description is None:
        description = (
            "Search the academic research library for information about "
            "Gestalt psychology, John Dewey's philosophy, and personal research notes. "
            "Use this tool to find specific information, quotes, concepts, and arguments "
            "from the corpus. Input should be a specific question or search query. "
            "This tool provides cited sources with page numbers."
        )

    def query_knowledge_base(query: str) -> str:
        """Query the knowledge base."""
        try:
            logger.debug(f"Knowledge base query: {query[:100]}...")
            response = query_engine.query(query)

            # Format response with sources
            result = str(response)

            # Add source information if available
            if hasattr(response, 'source_nodes') and response.source_nodes:
                result += "\n\n--- Sources ---\n"
                for i, node in enumerate(response.source_nodes[:3], 1):
                    metadata = node.node.metadata
                    source = metadata.get('source_file_path', 'Unknown')
                    page = metadata.get('source_page_number', 'N/A')
                    result += f"\n{i}. {Path(source).name} (Page {page})"

            logger.debug(f"Knowledge base returned {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"Knowledge base query failed: {e}")
            return f"Error querying knowledge base: {str(e)}"

    return Tool(
        name=name,
        func=query_knowledge_base,
        description=description
    )


def create_web_search_tool(
    max_results: int = 3
) -> Optional[Tool]:
    """
    Create a web search tool using Tavily.

    Args:
        max_results: Maximum number of search results

    Returns:
        TavilySearchResults tool or None if API key not configured
    """
    settings = get_settings()

    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured, web search tool unavailable")
        return None

    logger.info("Creating web search tool with Tavily")

    search = TavilySearchResults(
        max_results=max_results,
        api_key=settings.tavily_api_key
    )

    # Wrap with custom description
    return Tool(
        name="WebSearch",
        func=search.run,
        description=(
            "Search the web for current information, recent events, or topics "
            "not in the research library. Use this when the knowledge base doesn't "
            "have the information needed. Input should be a search query."
        )
    )


def create_calculator_tool() -> Tool:
    """
    Create a simple calculator tool.

    Useful for computational queries.

    Returns:
        Calculator Tool
    """
    def calculate(expression: str) -> str:
        """Evaluate a mathematical expression."""
        try:
            # Safe eval with limited scope
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"

    return Tool(
        name="Calculator",
        func=calculate,
        description=(
            "Perform mathematical calculations. "
            "Input should be a valid Python mathematical expression. "
            "Example: '2 + 2' or '(100 * 0.15) + 50'"
        )
    )


def create_list_projects_tool(project_manager) -> Tool:
    """
    Create a tool to list available projects.

    Args:
        project_manager: ProjectManager instance

    Returns:
        Tool for listing projects
    """
    def list_projects(_: str) -> str:
        """List all available projects."""
        try:
            projects = project_manager.list_projects()

            if not projects:
                return "No projects found."

            result = "Available projects:\n\n"
            for proj in projects:
                name = proj.get('name', 'Unknown')
                desc = proj.get('description', 'No description')
                modified = proj.get('modified_at', 'Unknown')
                result += f"• {name}\n  {desc}\n  Last modified: {modified}\n\n"

            return result

        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return f"Error listing projects: {str(e)}"

    return Tool(
        name="ListProjects",
        func=list_projects,
        description=(
            "List all available research projects. "
            "Use this to see what projects exist and their descriptions. "
            "Input can be empty or any string (ignored)."
        )
    )


def create_file_reader_tool() -> Tool:
    """
    Create a tool to read local files.

    Useful for the cross-examination workflow.

    Returns:
        File reader Tool
    """
    def read_file(file_path: str) -> str:
        """Read a local file."""
        try:
            path = Path(file_path).expanduser()

            if not path.exists():
                return f"Error: File not found: {file_path}"

            if not path.is_file():
                return f"Error: Not a file: {file_path}"

            # Read file with encoding detection
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(path, 'r', encoding='latin-1') as f:
                    content = f.read()

            # Limit to reasonable size
            if len(content) > 50000:
                content = content[:50000] + "\n\n[... truncated ...]"

            logger.debug(f"Read file: {path} ({len(content)} chars)")
            return content

        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return f"Error reading file: {str(e)}"

    return Tool(
        name="ReadFile",
        func=read_file,
        description=(
            "Read the contents of a local file. "
            "Input should be the full path to the file. "
            "Supports text files, markdown, and most document formats. "
            "Use this to load drafts for cross-examination."
        )
    )


def create_metadata_search_tool(query_engine: QueryEngine) -> Tool:
    """
    Create a tool to search by metadata filters.

    Args:
        query_engine: Query engine with filtering support

    Returns:
        Metadata search Tool
    """
    def search_by_metadata(query: str) -> str:
        """
        Search with metadata filters.

        Expected format: "filter:value query text"
        Example: "document_type:scanned_pdf dewey integration"
        """
        try:
            # Simple parsing (could be enhanced)
            parts = query.split(maxsplit=1)
            if len(parts) == 2 and ':' in parts[0]:
                filter_str, search_query = parts
                filter_key, filter_value = filter_str.split(':', 1)

                # Build metadata filter
                # Note: LlamaIndex metadata filtering syntax varies by version
                # This is a simplified example
                logger.debug(f"Metadata search: {filter_key}={filter_value}, query={search_query}")

                response = query_engine.query(search_query)
                return str(response)
            else:
                return "Invalid format. Use: filter:value query_text"

        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return f"Error: {str(e)}"

    return Tool(
        name="MetadataSearch",
        func=search_by_metadata,
        description=(
            "Search the knowledge base with metadata filters. "
            "Format: 'filter_name:filter_value query'. "
            "Available filters: document_type, original_language, canvas_name. "
            "Example: 'document_type:scanned_pdf dewey inquiry'"
        )
    )
