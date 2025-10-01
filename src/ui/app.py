"""
Chainlit application - ADHD-friendly chat interface.

This module implements the main UI with clean, distraction-free design
and visual feedback for agent reasoning steps.
"""

import asyncio
from pathlib import Path
from typing import Optional

import chainlit as cl
from loguru import logger

from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from ..storage import VectorStoreManager, ProjectManager
from ..retrieval import HybridRetriever, create_reranker
from ..agent import create_agent, create_llm, create_agent_config
from ..config import get_settings


# Global settings
settings = get_settings()

# Initialize components
project_manager = ProjectManager()


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session."""

    # Welcome message
    welcome_msg = """# 🎓 Academic RAG Assistant

Welcome! I'm your ADHD-friendly research assistant.

**I can help you:**
- Search your research library (Dewey, Gestalt psychology, personal notes)
- Cross-examine drafts against your corpus
- Search Zotero references
- Find and add open-access papers
- Answer questions about your research

**Current project:** Loading...

*Type your question or command to begin.*
"""

    await cl.Message(content=welcome_msg).send()

    try:
        # Set up LlamaIndex global settings
        await setup_llamaindex()

        # Load default project or show project selection
        await load_project_ui()

    except Exception as e:
        logger.error(f"Initialization error: {e}")
        await cl.Message(
            content=f"⚠️ Initialization error: {str(e)}\n\n"
                    f"Please check your configuration and try again."
        ).send()


async def setup_llamaindex():
    """Set up LlamaIndex global settings."""

    logger.info("Setting up LlamaIndex")

    # Set embedding model
    embed_model = HuggingFaceEmbedding(
        model_name=settings.embedding_model
    )

    Settings.embed_model = embed_model
    Settings.chunk_size = settings.chunk_size
    Settings.chunk_overlap = settings.chunk_overlap

    # Set LLM
    llm = create_llm()
    Settings.llm = llm

    logger.success("LlamaIndex configured")


async def load_project_ui():
    """Show project selection UI."""

    # List available projects
    projects = project_manager.list_projects()

    if not projects:
        await cl.Message(
            content="📂 No projects found. Create one with: `/create-project <name>`"
        ).send()
        return

    # Load most recent project
    recent_project = projects[0]
    project_name = recent_project['name']

    await load_project(project_name)


async def load_project(project_name: str):
    """
    Load a project and initialize the agent.

    Args:
        project_name: Name of project to load
    """

    logger.info(f"Loading project: {project_name}")

    try:
        # Show loading step
        async with cl.Step(name=f"Loading project: {project_name}") as step:
            # Load vector store
            vector_store = VectorStoreManager(project_name)

            if not vector_store.exists():
                step.output = f"❌ Project '{project_name}' has no indexed data yet."
                await cl.Message(
                    content=f"Project '{project_name}' loaded, but no documents indexed yet.\n"
                            f"Add documents with: `/ingest <path>`"
                ).send()
                return

            # Load index
            index = vector_store.load_index()
            step.output = f"✅ Loaded {vector_store.get_stats().get('num_vectors', 'unknown')} vectors"

        # Create retrieval pipeline
        async with cl.Step(name="Initializing retrieval pipeline") as step:
            hybrid_retriever = HybridRetriever(
                index=index,
                vector_top_k=5,
                bm25_top_k=5,
                fusion_top_k=settings.top_k_retrieval
            )

            reranker = create_reranker()

            query_engine = index.as_query_engine(
                retriever=hybrid_retriever.get_retriever(),
                node_postprocessors=[reranker.get_postprocessor()]
            )

            step.output = "✅ Hybrid search + re-ranking ready"

        # Create agent
        async with cl.Step(name="Creating agent") as step:
            agent = create_agent(
                query_engine=query_engine,
                index=index,
                project_manager=project_manager,
                enable_memory=True
            )

            step.output = "✅ Agent initialized with tools"

        # Store in session
        cl.user_session.set("agent", agent)
        cl.user_session.set("project_name", project_name)
        cl.user_session.set("index", index)
        cl.user_session.set("query_engine", query_engine)

        # Success message
        await cl.Message(
            content=f"✅ **Project loaded:** {project_name}\n\n"
                    f"Ready to help with your research!"
        ).send()

    except Exception as e:
        logger.error(f"Failed to load project: {e}")
        await cl.Message(
            content=f"❌ Error loading project: {str(e)}"
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages."""

    user_input = message.content

    # Check for commands
    if user_input.startswith("/"):
        await handle_command(user_input)
        return

    # Get agent from session
    agent = cl.user_session.get("agent")

    if not agent:
        await cl.Message(
            content="⚠️ No project loaded. Use `/load <project_name>` first."
        ).send()
        return

    # Create response message
    response_msg = cl.Message(content="")
    await response_msg.send()

    try:
        # Show thinking step
        async with cl.Step(name="🤔 Reasoning...") as step:
            # Get thread ID from session
            thread_id = cl.user_session.get("thread_id", "default")

            # Create config
            config = create_agent_config(thread_id=thread_id)

            # Run agent
            inputs = {"messages": [("user", user_input)]}

            # Execute agent
            result = await asyncio.to_thread(
                agent.invoke,
                inputs,
                config
            )

            # Extract response
            messages = result.get("messages", [])

            if messages:
                final_msg = messages[-1]
                response_text = final_msg.content if hasattr(final_msg, 'content') else str(final_msg)
            else:
                response_text = "No response generated."

            step.output = "✅ Complete"

        # Update response
        response_msg.content = response_text
        await response_msg.update()

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        response_msg.content = f"❌ Error: {str(e)}"
        await response_msg.update()


async def handle_command(command: str):
    """Handle slash commands."""

    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd == "/help":
        help_text = """# Commands

**Project Management:**
- `/projects` - List all projects
- `/load <name>` - Load a project
- `/create <name>` - Create new project
- `/info` - Show current project info

**Document Management:**
- `/ingest <path>` - Ingest documents from path

**System:**
- `/help` - Show this help
"""
        await cl.Message(content=help_text).send()

    elif cmd == "/projects":
        projects = project_manager.list_projects()

        if not projects:
            await cl.Message(content="No projects found.").send()
        else:
            result = "# Available Projects\n\n"
            for proj in projects:
                result += f"**{proj['name']}**\n{proj.get('description', 'No description')}\n\n"

            await cl.Message(content=result).send()

    elif cmd == "/load":
        if not args:
            await cl.Message(content="Usage: `/load <project_name>`").send()
            return

        await load_project(args.strip())

    elif cmd == "/create":
        if not args:
            await cl.Message(content="Usage: `/create <project_name>`").send()
            return

        try:
            project_manager.create_project(args.strip())
            await cl.Message(content=f"✅ Project '{args}' created!").send()
        except Exception as e:
            await cl.Message(content=f"❌ Error: {str(e)}").send()

    elif cmd == "/info":
        project_name = cl.user_session.get("project_name")

        if not project_name:
            await cl.Message(content="No project loaded.").send()
            return

        try:
            info = project_manager.get_project_info(project_name)
            result = f"""# Project: {info['name']}

**Description:** {info.get('description', 'None')}

**Created:** {info.get('created_at', 'Unknown')}
**Modified:** {info.get('modified_at', 'Unknown')}

**Vector Store:**
- Vectors: {info.get('vector_store', {}).get('num_vectors', 'Unknown')}
- Directory: {info.get('vector_store', {}).get('vector_store_dir', 'Unknown')}
"""
            await cl.Message(content=result).send()
        except Exception as e:
            await cl.Message(content=f"❌ Error: {str(e)}").send()

    else:
        await cl.Message(content=f"Unknown command: {cmd}\nType `/help` for help.").send()


@cl.on_chat_end
async def on_chat_end():
    """Clean up when chat ends."""
    logger.info("Chat session ended")


if __name__ == "__main__":
    # Run with: chainlit run src/ui/app.py
    pass
