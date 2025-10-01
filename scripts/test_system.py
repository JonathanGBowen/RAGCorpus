#!/usr/bin/env python3
"""
Test script to verify the RAG system is working correctly.

This script tests all major components without requiring a full corpus.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import get_settings
from src.storage import VectorStoreManager, ProjectManager
from src.ingestion import DocumentPipeline
from src.retrieval import HybridRetriever, create_reranker
from src.agent import create_agent, create_llm

from llama_index.core import Settings, Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


def test_configuration():
    """Test configuration loading."""
    logger.info("Testing configuration...")
    settings = get_settings()

    logger.info(f"  LLM Provider: {settings.default_llm_provider}")
    logger.info(f"  Embedding Model: {settings.embedding_model}")
    logger.info(f"  Chunk Size: {settings.chunk_size}")

    assert settings.chunk_size > 0, "Invalid chunk size"
    logger.success("✅ Configuration OK")


def test_llm():
    """Test LLM client."""
    logger.info("Testing LLM connection...")

    try:
        llm = create_llm()
        response = llm.invoke("Say 'Hello'")
        logger.info(f"  LLM Response: {response.content[:50]}...")
        logger.success("✅ LLM OK")
    except Exception as e:
        logger.error(f"❌ LLM test failed: {e}")
        return False

    return True


def test_embeddings():
    """Test embedding model."""
    logger.info("Testing embedding model...")

    try:
        embed_model = HuggingFaceEmbedding(
            model_name=get_settings().embedding_model
        )

        test_text = "This is a test document about philosophy."
        embedding = embed_model.get_text_embedding(test_text)

        logger.info(f"  Embedding dimension: {len(embedding)}")
        assert len(embedding) > 0, "Empty embedding"

        logger.success("✅ Embeddings OK")
    except Exception as e:
        logger.error(f"❌ Embedding test failed: {e}")
        return False

    return True


def test_project_management():
    """Test project creation and management."""
    logger.info("Testing project management...")

    pm = ProjectManager()

    # Create test project
    test_project = "test_project_temp"

    # Clean up if exists
    if pm.project_exists(test_project):
        pm.delete_project(test_project)

    # Create new
    pm.create_project(test_project, description="Test project")

    assert pm.project_exists(test_project), "Project creation failed"

    # Get info
    info = pm.get_project_info(test_project)
    assert info['name'] == test_project, "Project info mismatch"

    # Clean up
    pm.delete_project(test_project)

    logger.success("✅ Project management OK")
    return True


def test_ingestion():
    """Test document ingestion."""
    logger.info("Testing ingestion pipeline...")

    # Create test project
    pm = ProjectManager()
    test_project = "test_ingest_temp"

    if pm.project_exists(test_project):
        pm.delete_project(test_project)

    pm.create_project(test_project)

    # Create test documents
    test_docs = [
        Document(
            text="John Dewey was an American philosopher. He wrote about pragmatism and education.",
            metadata={"source": "test1", "topic": "dewey"}
        ),
        Document(
            text="Gestalt psychology focuses on perception and problem solving. Key figures include Koffka and Köhler.",
            metadata={"source": "test2", "topic": "gestalt"}
        ),
        Document(
            text="The concept of integration in Dewey's philosophy relates to the unification of experience.",
            metadata={"source": "test3", "topic": "integration"}
        )
    ]

    # Set up embeddings
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=get_settings().embedding_model
    )

    # Create index
    vector_store = VectorStoreManager(test_project)
    storage_context = vector_store.get_storage_context()

    pipeline = DocumentPipeline(test_project)
    index = pipeline.create_index(test_docs, storage_context)

    # Verify
    stats = vector_store.get_stats()
    logger.info(f"  Created index with {stats.get('num_vectors', 0)} vectors")

    # Clean up
    pm.delete_project(test_project)

    logger.success("✅ Ingestion OK")
    return True


def test_retrieval():
    """Test hybrid retrieval."""
    logger.info("Testing retrieval pipeline...")

    # Create test project
    pm = ProjectManager()
    test_project = "test_retrieval_temp"

    if pm.project_exists(test_project):
        pm.delete_project(test_project)

    pm.create_project(test_project)

    # Create test documents
    test_docs = [
        Document(text="Dewey's theory of inquiry emphasizes scientific method."),
        Document(text="Gestalt psychology studies perception and cognition."),
        Document(text="Integration is a key concept in pragmatic philosophy.")
    ]

    # Set up
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=get_settings().embedding_model
    )
    Settings.llm = create_llm()

    # Create index
    vector_store = VectorStoreManager(test_project)
    storage_context = vector_store.get_storage_context()

    pipeline = DocumentPipeline(test_project)
    index = pipeline.create_index(test_docs, storage_context)

    # Test retrieval
    retriever = HybridRetriever(index)
    results = retriever.retrieve("What is Dewey's theory?")

    logger.info(f"  Retrieved {len(results)} results")
    assert len(results) > 0, "No results retrieved"

    # Test re-ranker
    reranker = create_reranker()
    reranked = reranker.rerank("What is Dewey's theory?", results)

    logger.info(f"  Re-ranked to {len(reranked)} results")

    # Clean up
    pm.delete_project(test_project)

    logger.success("✅ Retrieval OK")
    return True


def test_agent():
    """Test agent creation."""
    logger.info("Testing agent...")

    # Create minimal test setup
    pm = ProjectManager()
    test_project = "test_agent_temp"

    if pm.project_exists(test_project):
        pm.delete_project(test_project)

    pm.create_project(test_project)

    # Create test doc
    test_docs = [
        Document(text="This is a test document about Dewey and Gestalt psychology.")
    ]

    # Set up
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=get_settings().embedding_model
    )
    Settings.llm = create_llm()

    # Create index
    vector_store = VectorStoreManager(test_project)
    storage_context = vector_store.get_storage_context()

    pipeline = DocumentPipeline(test_project)
    index = pipeline.create_index(test_docs, storage_context)

    # Create query engine
    query_engine = index.as_query_engine()

    # Create agent
    agent = create_agent(query_engine)

    logger.info("  Agent created successfully")

    # Clean up
    pm.delete_project(test_project)

    logger.success("✅ Agent OK")
    return True


def main():
    """Run all tests."""
    logger.info("=== RAG System Test Suite ===\n")

    tests = [
        ("Configuration", test_configuration),
        ("LLM", test_llm),
        ("Embeddings", test_embeddings),
        ("Project Management", test_project_management),
        ("Ingestion", test_ingestion),
        ("Retrieval", test_retrieval),
        ("Agent", test_agent),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            logger.error(f"❌ {name} test failed: {e}")
            failed += 1

        logger.info("")  # Blank line

    # Summary
    logger.info("=" * 50)
    logger.info(f"Tests Passed: {passed}/{len(tests)}")
    logger.info(f"Tests Failed: {failed}/{len(tests)}")

    if failed == 0:
        logger.success("\n🎉 All tests passed! System is ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Run: python scripts/ingest_corpus.py")
        logger.info("2. Run: chainlit run src/ui/app.py")
    else:
        logger.warning(f"\n⚠️ {failed} test(s) failed. Please check configuration.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
