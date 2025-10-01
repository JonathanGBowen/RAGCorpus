#!/usr/bin/env python3
"""
Example: Cross-examine a draft against the library.

This demonstrates the cross-examination workflow.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from src.config import get_settings
from src.storage import VectorStoreManager
from src.agent.cross_examine import CrossExaminationTool
from src.agent import create_llm


def main():
    """Cross-examine a draft."""

    settings = get_settings()

    print("=== Cross-Examination Tool ===\n")

    # Setup
    print("Setting up...")
    Settings.embed_model = HuggingFaceEmbedding(model_name=settings.embedding_model)
    Settings.llm = create_llm()

    # Load project
    project_name = input("Enter project name: ").strip()

    vector_store = VectorStoreManager(project_name)

    if not vector_store.exists():
        print(f"\n❌ Project '{project_name}' not found.")
        return

    print(f"Loading project '{project_name}'...")
    index = vector_store.load_index()

    # Create query engine
    query_engine = index.as_query_engine()

    # Create cross-examination tool
    cross_examiner = CrossExaminationTool(query_engine, Settings.llm)

    # Get draft path
    draft_path = input("\nEnter path to your draft: ").strip()

    if not Path(draft_path).exists():
        print(f"❌ File not found: {draft_path}")
        return

    # Get focus concept (optional)
    focus = input("Focus concept (optional, press Enter to skip): ").strip()
    focus = focus if focus else None

    # Run cross-examination
    print("\n🔍 Cross-examining draft...\n")

    result = cross_examiner.cross_examine(draft_path, focus)

    # Display result
    print("=" * 60)
    print(result)
    print("=" * 60)


if __name__ == "__main__":
    main()
