"""
ChromaDB vector store management with persistence.

This module provides a wrapper around ChromaDB with project-based
organization and persistence.
"""

from pathlib import Path
from typing import Optional, List

import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger

from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.schema import Document

from ..config import get_settings


class VectorStoreManager:
    """
    Manager for ChromaDB vector storage with persistence.

    Provides project-based organization with automatic persistence
    to local directories.
    """

    def __init__(self, project_name: str):
        """
        Initialize vector store manager for a project.

        Args:
            project_name: Name of the project
        """
        self.settings = get_settings()
        self.project_name = project_name

        # Get project-specific directories
        self.vector_store_dir = self.settings.get_vector_store_dir(project_name)
        self.storage_dir = self.settings.get_storage_dir(project_name)

        logger.info(f"Initializing vector store for project: {project_name}")
        logger.debug(f"Vector store dir: {self.vector_store_dir}")
        logger.debug(f"Storage dir: {self.storage_dir}")

        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.vector_store_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Collection name for this project
        self.collection_name = f"{project_name}_collection"

        # Will be initialized when needed
        self._vector_store: Optional[ChromaVectorStore] = None
        self._storage_context: Optional[StorageContext] = None

    def get_or_create_collection(self) -> ChromaVectorStore:
        """
        Get existing collection or create new one.

        Returns:
            ChromaVectorStore instance
        """
        if self._vector_store is None:
            # Get or create ChromaDB collection
            try:
                chroma_collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name
                )
                logger.info(f"Using collection: {self.collection_name}")
            except Exception as e:
                logger.error(f"Failed to get/create collection: {e}")
                raise

            # Wrap in LlamaIndex vector store
            self._vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        return self._vector_store

    def get_storage_context(self) -> StorageContext:
        """
        Get storage context for this project.

        Returns:
            StorageContext instance
        """
        if self._storage_context is None:
            vector_store = self.get_or_create_collection()

            # Check if storage directory has existing data
            docstore_path = self.storage_dir / "docstore.json"
            
            if docstore_path.exists():
                # Load existing storage context
                self._storage_context = StorageContext.from_defaults(
                    vector_store=vector_store,
                    persist_dir=str(self.storage_dir)
                )
            else:
                # Create fresh storage context
                self._storage_context = StorageContext.from_defaults(
                    vector_store=vector_store
                )
                # Set the persist dir for future saves
                self._storage_context.persist(persist_dir=str(self.storage_dir))

        return self._storage_context

    def create_index(self, documents: List[Document]) -> VectorStoreIndex:
        """
        Create a new vector index from documents.

        Args:
            documents: List of documents to index

        Returns:
            VectorStoreIndex
        """
        logger.info(f"Creating index for {len(documents)} documents")

        storage_context = self.get_storage_context()

        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=True
        )

        # Persist to disk
        self.persist()

        logger.success(f"Index created and persisted for project: {self.project_name}")
        return index

    def load_index(self) -> VectorStoreIndex:
        """
        Load existing index from storage.

        Returns:
            VectorStoreIndex

        Raises:
            ValueError: If no index exists for this project
        """
        logger.info(f"Loading index for project: {self.project_name}")

        if not self.exists():
            raise ValueError(
                f"No index found for project '{self.project_name}'. "
                f"Create one first with create_index()."
            )

        storage_context = self.get_storage_context()

        index = load_index_from_storage(storage_context)

        logger.success(f"Index loaded successfully")
        return index

    def add_documents(self, index: VectorStoreIndex, documents: List[Document]) -> None:
        """
        Add new documents to an existing index.

        Args:
            index: Existing VectorStoreIndex
            documents: Documents to add
        """
        logger.info(f"Adding {len(documents)} documents to index")

        for doc in documents:
            index.insert(doc)

        # Persist changes
        self.persist()

        logger.success(f"Added {len(documents)} documents")

    def persist(self) -> None:
        """
        Persist index and storage to disk.
        """
        if self._storage_context is not None:
            self._storage_context.persist(persist_dir=str(self.storage_dir))
            logger.debug("Index persisted to disk")

    def exists(self) -> bool:
        """
        Check if an index exists for this project.

        Returns:
            True if index exists, False otherwise
        """
        # Check if storage directory has index files
        docstore_path = self.storage_dir / "docstore.json"
        return docstore_path.exists()

    def delete(self) -> None:
        """
        Delete all data for this project.

        WARNING: This is irreversible!
        """
        logger.warning(f"Deleting all data for project: {self.project_name}")

        # Delete ChromaDB collection
        try:
            self.chroma_client.delete_collection(name=self.collection_name)
        except Exception as e:
            logger.warning(f"Failed to delete collection: {e}")

        # Delete storage directory
        import shutil
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)

        if self.vector_store_dir.exists():
            shutil.rmtree(self.vector_store_dir)

        logger.warning("Project data deleted")

    def get_stats(self) -> dict:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with stats
        """
        stats = {
            "project_name": self.project_name,
            "exists": self.exists(),
            "vector_store_dir": str(self.vector_store_dir),
            "storage_dir": str(self.storage_dir)
        }

        if self.exists():
            try:
                # Get collection stats
                collection = self.chroma_client.get_collection(self.collection_name)
                stats["num_vectors"] = collection.count()
            except Exception as e:
                logger.warning(f"Failed to get collection stats: {e}")
                stats["num_vectors"] = None

        return stats

    def list_collections(self) -> List[str]:
        """
        List all collections in the ChromaDB instance.

        Returns:
            List of collection names
        """
        collections = self.chroma_client.list_collections()
        return [col.name for col in collections]

    def reset_collection(self) -> None:
        """
        Delete and recreate the collection (clears all vectors).
        """
        logger.warning(f"Resetting collection: {self.collection_name}")

        try:
            self.chroma_client.delete_collection(name=self.collection_name)
        except Exception:
            pass

        self._vector_store = None
        self._storage_context = None

        logger.info("Collection reset complete")
