#!/usr/bin/env python3
"""
Simple example: Query the knowledge base.

This demonstrates basic querying without the full UI.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from src.config import get_settings
from src.storage import VectorStoreManager
from src.retrieval import HybridRetriever, create_reranker
from src.agent import create_llm


def main():
    """Run a simple query."""

    # Configuration
    settings = get_settings()

    print("=== Simple Knowledge Base Query ===\n")

    # Setup
    print("Setting up...")
    Settings.embed_model = HuggingFaceEmbedding(model_name=settings.embedding_model)
    Settings.llm = create_llm()

    # Load project
    project_name = input("Enter project name (default: 'default'): ").strip() or "default"

    vector_store = VectorStoreManager(project_name)

    if not vector_store.exists():
        print(f"\n❌ Project '{project_name}' not found or has no data.")
        print("Create a project first with: python scripts/ingest_corpus.py")
        return

    print(f"Loading project '{project_name}'...")
    index = vector_store.load_index()

    # Create retrieval pipeline
    print("Setting up retrieval pipeline...")
    retriever = HybridRetriever(index)
    reranker = create_reranker()

    query_engine = index.as_query_engine(
        retriever=retriever.get_retriever(),
        node_postprocessors=[reranker.get_postprocessor()]
    )

    print("\n✅ Ready! Ask your questions (type 'quit' to exit)\n")

    # Query loop
    while True:
        query = input("Question: ").strip()

        if not query or query.lower() == 'quit':
            break

        print("\nSearching...")

        # Query
        response = query_engine.query(query)

        # Display response
        print(f"\n{response}\n")

        # Display sources
        if hasattr(response, 'source_nodes') and response.source_nodes:
            print("--- Sources ---")
            for i, node in enumerate(response.source_nodes[:3], 1):
                metadata = node.node.metadata
                source = Path(metadata.get('source_file_path', 'Unknown')).name
                page = metadata.get('source_page_number', 'N/A')
                print(f"{i}. {source} (Page {page})")

        print()

    print("Goodbye!")


if __name__ == "__main__":
    main()
