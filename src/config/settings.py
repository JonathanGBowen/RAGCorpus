"""
Settings and configuration management using Pydantic.

This module provides type-safe configuration management with environment
variable support and validation.
"""

from pathlib import Path
from typing import Literal, Optional
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via .env file or environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    google_api_key: Optional[str] = Field(None, description="Google Gemini API key")
    ollama_base_url: str = Field("http://localhost:11434", description="Ollama server URL")
    default_llm_provider: Literal["gemini", "ollama"] = Field(
        "gemini", description="Default LLM provider"
    )
    gemini_model: str = Field("gemini-1.5-pro", description="Gemini model name")
    ollama_model: str = Field("llama3.1:8b", description="Ollama model name")

    # Embedding Configuration
    embedding_model: str = Field("BAAI/bge-m3", description="Embedding model from HuggingFace")
    reranker_model: str = Field(
        "BAAI/bge-reranker-base", description="Cross-encoder reranker model"
    )

    # Zotero Configuration
    zotero_user_id: Optional[str] = Field(None, description="Zotero user ID")
    zotero_api_key: Optional[str] = Field(None, description="Zotero API key")
    zotero_library_type: Literal["user", "group"] = Field(
        "user", description="Zotero library type"
    )

    # Web Search
    tavily_api_key: Optional[str] = Field(None, description="Tavily search API key")

    # Database Configuration
    database_url: Optional[str] = Field(
        None, description="PostgreSQL URL for Chainlit chat history"
    )

    # Chunking Configuration
    chunk_size: int = Field(512, description="Chunk size in tokens", ge=128, le=2048)
    chunk_overlap: int = Field(50, description="Overlap between chunks", ge=0, le=200)

    # Retrieval Configuration
    top_k_retrieval: int = Field(10, description="Number of chunks to retrieve", ge=1, le=50)
    rerank_top_n: int = Field(
        3, description="Number of chunks after re-ranking", ge=1, le=20
    )

    # OCR Configuration
    tesseract_cmd: Optional[str] = Field(
        None, description="Path to Tesseract executable (auto-detected if None)"
    )
    ocr_languages: str = Field("eng+deu", description="Tesseract language codes")
    ocr_dpi: int = Field(300, description="Target DPI for OCR", ge=150, le=600)

    # Translation Configuration
    translation_model: str = Field(
        "Helsinki-NLP/opus-mt-de-en", description="MarianMT translation model"
    )
    translation_batch_size: int = Field(8, description="Translation batch size", ge=1, le=32)

    # Storage Paths
    data_dir: Path = Field(Path("data"), description="Base data directory")
    projects_dir: Path = Field(Path("data/projects"), description="Projects directory")
    temp_dir: Path = Field(Path("data/temp"), description="Temporary files directory")

    @field_validator("projects_dir", "temp_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: Path | str) -> Path:
        """Convert strings to Path objects."""
        path = Path(v) if isinstance(v, str) else v
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_project_dir(self, project_name: str) -> Path:
        """Get the directory for a specific project."""
        project_dir = self.projects_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def get_vector_store_dir(self, project_name: str) -> Path:
        """Get the ChromaDB directory for a project."""
        vector_dir = self.get_project_dir(project_name) / "chroma_db"
        vector_dir.mkdir(parents=True, exist_ok=True)
        return vector_dir

    def get_storage_dir(self, project_name: str) -> Path:
        """Get the LlamaIndex storage directory for a project."""
        storage_dir = self.get_project_dir(project_name) / "storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings singleton
    """
    return Settings()
