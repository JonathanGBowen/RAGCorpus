#!/usr/bin/env python3
"""
Starter script for ingesting your academic corpus.

This script demonstrates how to use the ingestion pipeline
to load documents into a project.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import get_settings
from src.storage import VectorStoreManager, ProjectManager
from src.ingestion import DocumentPipeline


def main():
    """Main ingestion script."""

    logger.info("=== RAG Corpus Ingestion Script ===")

    # Get settings
    settings = get_settings()

    # Project name
    project_name = input("Enter project name (or press Enter for 'default'): ").strip()
    if not project_name:
        project_name = "default"

    # Create or load project
    pm = ProjectManager()

    if not pm.project_exists(project_name):
        description = input("Project description: ").strip()
        logger.info(f"Creating new project: {project_name}")
        pm.create_project(project_name, description=description)
    else:
        logger.info(f"Using existing project: {project_name}")

    # Get corpus directory
    corpus_dir = input("Enter path to corpus directory: ").strip()

    if not corpus_dir:
        logger.error("No directory specified")
        return

    corpus_path = Path(corpus_dir).expanduser()

    if not corpus_path.exists():
        logger.error(f"Directory not found: {corpus_path}")
        return

    # Initialize pipeline
    logger.info("Initializing ingestion pipeline...")
    pipeline = DocumentPipeline(project_name=project_name)

    # Initialize vector store
    vector_store = VectorStoreManager(project_name)

    try:
        # Ingest directory
        logger.info(f"Ingesting documents from: {corpus_path}")

        if vector_store.exists():
            # Add to existing index
            logger.info("Adding to existing index...")
            index = vector_store.load_index()

            # Ingest documents
            documents = pipeline.ingest_directory(
                corpus_path,
                recursive=True
            )

            # Add to index
            vector_store.add_documents(index, documents)

        else:
            # Create new index
            logger.info("Creating new index...")
            storage_context = vector_store.get_storage_context()

            index = pipeline.ingest_and_index(
                source=corpus_path,
                is_directory=True,
                storage_context=storage_context,
                recursive=True
            )

        # Show stats
        stats = vector_store.get_stats()
        logger.success(f"\n=== Ingestion Complete ===")
        logger.success(f"Project: {project_name}")
        logger.success(f"Vectors: {stats.get('num_vectors', 'Unknown')}")
        logger.success(f"\nYou can now use this project in the Chainlit UI!")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise


if __name__ == "__main__":
    main()
