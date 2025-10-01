"""
Unified document ingestion pipeline using LlamaIndex.

This module orchestrates the complete ingestion workflow:
Loading -> Transforming -> Indexing
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum

from llama_index.core import (
    SimpleDirectoryReader,
    Document,
    VectorStoreIndex,
    StorageContext
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from loguru import logger

from .ocr_processor import OCRProcessor
from .translator import GermanTranslator
from .canvas_parser import ObsidianCanvasParser
from ..config import get_settings


class DocumentType(str, Enum):
    """Enumeration of supported document types."""
    CLEAN_PDF = "clean_pdf"
    SCANNED_PDF = "scanned_pdf"
    GERMAN_TEXT = "german_text"
    OBSIDIAN_CANVAS = "obsidian_canvas"
    PERSONAL_NOTE = "personal_note"
    MARKDOWN = "markdown"
    TEXT = "text"
    AUTO_DETECT = "auto_detect"


class DocumentPipeline:
    """
    Unified pipeline for document ingestion.

    Handles all stages:
    1. Loading: Read documents from various sources
    2. Transforming: OCR, translation, parsing, chunking
    3. Indexing: Create vector embeddings and store
    """

    def __init__(
        self,
        project_name: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ):
        """
        Initialize the ingestion pipeline.

        Args:
            project_name: Name of the project for organizing data
            chunk_size: Token size for chunks (from settings if None)
            chunk_overlap: Overlap between chunks (from settings if None)
        """
        self.settings = get_settings()
        self.project_name = project_name

        # Initialize processors
        self.ocr_processor = OCRProcessor()
        self.translator = GermanTranslator()
        self.canvas_parser = ObsidianCanvasParser()

        # Initialize chunker
        self.chunk_size = chunk_size or self.settings.chunk_size
        self.chunk_overlap = chunk_overlap or self.settings.chunk_overlap

        self.chunker = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        logger.info(
            f"Initialized pipeline for project '{project_name}' "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap})"
        )

    def ingest_directory(
        self,
        directory: Path | str,
        recursive: bool = True,
        file_types: Optional[List[str]] = None,
        document_type: DocumentType = DocumentType.AUTO_DETECT
    ) -> List[Document]:
        """
        Ingest all documents from a directory.

        Args:
            directory: Directory path to ingest
            recursive: Whether to recursively search subdirectories
            file_types: List of file extensions to include (e.g., ['.pdf', '.txt'])
            document_type: How to process documents

        Returns:
            List of processed LlamaIndex Documents
        """
        directory = Path(directory)
        logger.info(f"Ingesting directory: {directory}")

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        # Collect all files
        if file_types is None:
            file_types = ['.pdf', '.txt', '.md', '.canvas']

        pattern = "**/*" if recursive else "*"
        all_files = []

        for ext in file_types:
            files = list(directory.glob(f"{pattern}{ext}"))
            all_files.extend(files)

        logger.info(f"Found {len(all_files)} files to process")

        # Process each file
        documents = []
        for file_path in all_files:
            try:
                doc_list = self.ingest_file(file_path, document_type)
                documents.extend(doc_list)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue

        logger.success(f"Ingested {len(documents)} documents from {len(all_files)} files")
        return documents

    def ingest_file(
        self,
        file_path: Path | str,
        document_type: DocumentType = DocumentType.AUTO_DETECT
    ) -> List[Document]:
        """
        Ingest a single file.

        Args:
            file_path: Path to file
            document_type: How to process the file

        Returns:
            List of Documents (usually one, but multiple for .canvas files)
        """
        file_path = Path(file_path)
        logger.info(f"Ingesting file: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Auto-detect document type if needed
        if document_type == DocumentType.AUTO_DETECT:
            document_type = self._detect_document_type(file_path)
            logger.debug(f"Auto-detected type: {document_type}")

        # Route to appropriate processor
        if document_type == DocumentType.OBSIDIAN_CANVAS:
            return self.canvas_parser.parse_canvas(file_path)

        elif document_type == DocumentType.SCANNED_PDF:
            doc = self.ocr_processor.process_pdf(file_path)
            return [doc]

        elif document_type == DocumentType.GERMAN_TEXT:
            doc = self.translator.translate_file(file_path)
            return [doc]

        else:
            # Use SimpleDirectoryReader for standard formats
            reader = SimpleDirectoryReader(input_files=[str(file_path)])
            docs = reader.load_data()

            # Add metadata
            for doc in docs:
                doc.metadata.update({
                    "source_file_path": str(file_path.absolute()),
                    "document_type": document_type.value,
                    "processing_method": "simple_directory_reader"
                })

            return docs

    def chunk_documents(self, documents: List[Document]) -> List[TextNode]:
        """
        Transform Documents into chunked Node objects.

        Args:
            documents: List of Documents to chunk

        Returns:
            List of TextNode objects (chunks)
        """
        logger.info(f"Chunking {len(documents)} documents")

        nodes = self.chunker.get_nodes_from_documents(documents)

        logger.success(
            f"Created {len(nodes)} nodes from {len(documents)} documents "
            f"(avg {len(nodes)/len(documents):.1f} nodes per doc)"
        )

        return nodes

    def create_index(
        self,
        documents: List[Document],
        storage_context: Optional[StorageContext] = None
    ) -> VectorStoreIndex:
        """
        Create a vector index from documents.

        This performs chunking, embedding, and storage.

        Args:
            documents: List of Documents to index
            storage_context: Optional storage context for persistence

        Returns:
            VectorStoreIndex
        """
        logger.info(f"Creating index from {len(documents)} documents")

        # Create index (this will handle chunking internally)
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            transformations=[self.chunker],
            show_progress=True
        )

        logger.success("Index created successfully")
        return index

    def ingest_and_index(
        self,
        source: Path | str,
        is_directory: bool = True,
        storage_context: Optional[StorageContext] = None,
        **kwargs
    ) -> VectorStoreIndex:
        """
        Complete end-to-end ingestion and indexing.

        Args:
            source: Path to file or directory
            is_directory: Whether source is a directory
            storage_context: Storage context for persistence
            **kwargs: Additional arguments for ingest_directory/ingest_file

        Returns:
            VectorStoreIndex ready for querying
        """
        logger.info(f"Starting end-to-end ingestion: {source}")

        # Load documents
        if is_directory:
            documents = self.ingest_directory(source, **kwargs)
        else:
            documents = self.ingest_file(source, **kwargs)

        if not documents:
            raise ValueError("No documents were loaded")

        # Create index
        index = self.create_index(documents, storage_context)

        logger.success(
            f"Pipeline complete: {len(documents)} documents indexed for project '{self.project_name}'"
        )

        return index

    def _detect_document_type(self, file_path: Path) -> DocumentType:
        """
        Auto-detect document type from file extension and content.

        Args:
            file_path: Path to file

        Returns:
            DocumentType enum
        """
        suffix = file_path.suffix.lower()

        # Check by extension
        if suffix == '.canvas':
            return DocumentType.OBSIDIAN_CANVAS

        elif suffix == '.md':
            return DocumentType.MARKDOWN

        elif suffix == '.txt':
            # Could be German text - do a quick check
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    sample = f.read(1000)
                if self.translator.detect_language(sample) == 'de':
                    return DocumentType.GERMAN_TEXT
            except Exception:
                pass
            return DocumentType.TEXT

        elif suffix == '.pdf':
            # Heuristic: assume scanned if filename contains certain keywords
            name_lower = file_path.stem.lower()
            scanned_indicators = ['scan', 'scanned', 'ocr', '1940', '1950', '1960']

            if any(indicator in name_lower for indicator in scanned_indicators):
                return DocumentType.SCANNED_PDF
            else:
                return DocumentType.CLEAN_PDF

        else:
            # Default to auto-detection
            return DocumentType.TEXT

    def add_custom_metadata(
        self,
        documents: List[Document],
        metadata: Dict[str, Any]
    ) -> List[Document]:
        """
        Add custom metadata to all documents.

        Args:
            documents: List of documents
            metadata: Dictionary of metadata to add

        Returns:
            Documents with updated metadata
        """
        for doc in documents:
            doc.metadata.update(metadata)

        logger.debug(f"Added metadata to {len(documents)} documents: {list(metadata.keys())}")
        return documents

    def filter_documents(
        self,
        documents: List[Document],
        min_length: int = 100,
        remove_empty: bool = True
    ) -> List[Document]:
        """
        Filter documents based on criteria.

        Args:
            documents: List of documents to filter
            min_length: Minimum text length
            remove_empty: Whether to remove empty documents

        Returns:
            Filtered list of documents
        """
        filtered = []

        for doc in documents:
            text = doc.text.strip()

            if remove_empty and not text:
                continue

            if len(text) < min_length:
                continue

            filtered.append(doc)

        logger.info(f"Filtered {len(documents)} -> {len(filtered)} documents")
        return filtered
