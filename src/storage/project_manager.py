"""
Project lifecycle management.

Manages creating, loading, saving, and organizing research projects.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from loguru import logger

from llama_index.core import VectorStoreIndex

from .vector_store import VectorStoreManager
from ..ingestion.pipeline import DocumentPipeline
from ..config import get_settings


class ProjectManager:
    """
    Manages the lifecycle of research projects.

    A project encapsulates:
    - Document corpus and metadata
    - Vector store and embeddings
    - Chat history (via Chainlit tags)
    - Project-specific settings
    """

    def __init__(self):
        """Initialize the project manager."""
        self.settings = get_settings()
        self.projects_dir = self.settings.projects_dir
        logger.info(f"Project manager initialized (projects dir: {self.projects_dir})")

    def create_project(
        self,
        project_name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VectorStoreManager:
        """
        Create a new project.

        Args:
            project_name: Unique name for the project
            description: Optional project description
            metadata: Optional metadata dictionary

        Returns:
            VectorStoreManager for the new project
        """
        logger.info(f"Creating new project: {project_name}")

        # Check if project already exists
        if self.project_exists(project_name):
            raise ValueError(f"Project '{project_name}' already exists")

        # Create project directory
        project_dir = self.settings.get_project_dir(project_name)

        # Create metadata file
        project_metadata = {
            "name": project_name,
            "description": description or "",
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        metadata_path = project_dir / "project.json"
        with open(metadata_path, 'w') as f:
            json.dump(project_metadata, f, indent=2)

        # Initialize vector store
        vector_store = VectorStoreManager(project_name)

        logger.success(f"Project '{project_name}' created successfully")
        return vector_store

    def load_project(self, project_name: str) -> VectorStoreManager:
        """
        Load an existing project.

        Args:
            project_name: Name of the project to load

        Returns:
            VectorStoreManager for the project

        Raises:
            ValueError: If project doesn't exist
        """
        logger.info(f"Loading project: {project_name}")

        if not self.project_exists(project_name):
            raise ValueError(f"Project '{project_name}' does not exist")

        # Update modified timestamp
        self._update_project_timestamp(project_name)

        # Load vector store
        vector_store = VectorStoreManager(project_name)

        logger.success(f"Project '{project_name}' loaded successfully")
        return vector_store

    def delete_project(self, project_name: str) -> None:
        """
        Delete a project and all its data.

        WARNING: This is irreversible!

        Args:
            project_name: Name of the project to delete
        """
        logger.warning(f"Deleting project: {project_name}")

        if not self.project_exists(project_name):
            raise ValueError(f"Project '{project_name}' does not exist")

        # Delete vector store data
        vector_store = VectorStoreManager(project_name)
        vector_store.delete()
        
        # Explicitly release resources (important for Windows file locking)
        del vector_store
        import gc
        gc.collect()
        import time
        time.sleep(0.3)  # Brief delay for Windows to release file handles

        # Delete project directory
        import shutil
        project_dir = self.settings.get_project_dir(project_name)
        if project_dir.exists():
            shutil.rmtree(project_dir)

        logger.warning(f"Project '{project_name}' deleted")

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all available projects.

        Returns:
            List of project metadata dictionaries
        """
        projects = []

        if not self.projects_dir.exists():
            return projects

        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                metadata_path = project_dir / "project.json"

                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        projects.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for {project_dir.name}: {e}")
                else:
                    # Create basic metadata if missing
                    projects.append({
                        "name": project_dir.name,
                        "description": "No description",
                        "created_at": "Unknown",
                        "modified_at": "Unknown"
                    })

        # Sort by modified time (most recent first)
        projects.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

        return projects

    def project_exists(self, project_name: str) -> bool:
        """
        Check if a project exists.

        Args:
            project_name: Name of the project

        Returns:
            True if project exists, False otherwise
        """
        project_dir = self.settings.get_project_dir(project_name)
        return project_dir.exists()

    def get_project_info(self, project_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a project.

        Args:
            project_name: Name of the project

        Returns:
            Dictionary with project information
        """
        if not self.project_exists(project_name):
            raise ValueError(f"Project '{project_name}' does not exist")

        # Load metadata
        metadata_path = self.settings.get_project_dir(project_name) / "project.json"

        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                info = json.load(f)
        else:
            info = {
                "name": project_name,
                "description": "No description",
                "created_at": "Unknown",
                "modified_at": "Unknown"
            }

        # Add vector store stats
        vector_store = VectorStoreManager(project_name)
        info["vector_store"] = vector_store.get_stats()

        return info

    def update_project_metadata(
        self,
        project_name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update project metadata.

        Args:
            project_name: Name of the project
            description: New description (None to keep existing)
            metadata: Metadata dictionary to merge
        """
        if not self.project_exists(project_name):
            raise ValueError(f"Project '{project_name}' does not exist")

        metadata_path = self.settings.get_project_dir(project_name) / "project.json"

        # Load existing metadata
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                current_metadata = json.load(f)
        else:
            current_metadata = {
                "name": project_name,
                "description": "",
                "created_at": datetime.now().isoformat(),
                "metadata": {}
            }

        # Update fields
        if description is not None:
            current_metadata["description"] = description

        if metadata is not None:
            current_metadata["metadata"].update(metadata)

        current_metadata["modified_at"] = datetime.now().isoformat()

        # Save
        with open(metadata_path, 'w') as f:
            json.dump(current_metadata, f, indent=2)

        logger.debug(f"Updated metadata for project: {project_name}")

    def _update_project_timestamp(self, project_name: str) -> None:
        """Update the modified_at timestamp for a project."""
        try:
            self.update_project_metadata(project_name)
        except Exception as e:
            logger.debug(f"Failed to update timestamp: {e}")

    def export_project(
        self,
        project_name: str,
        export_path: Path | str
    ) -> None:
        """
        Export a project to a zip file.

        Args:
            project_name: Name of the project
            export_path: Path for the exported zip file
        """
        import shutil

        if not self.project_exists(project_name):
            raise ValueError(f"Project '{project_name}' does not exist")

        export_path = Path(export_path)
        logger.info(f"Exporting project '{project_name}' to {export_path}")

        project_dir = self.settings.get_project_dir(project_name)

        # Create zip file
        shutil.make_archive(
            str(export_path.with_suffix('')),
            'zip',
            project_dir.parent,
            project_dir.name
        )

        logger.success(f"Project exported to {export_path}")

    def import_project(
        self,
        zip_path: Path | str,
        project_name: Optional[str] = None
    ) -> str:
        """
        Import a project from a zip file.

        Args:
            zip_path: Path to the zip file
            project_name: Optional new name for the project

        Returns:
            Name of the imported project
        """
        import shutil

        zip_path = Path(zip_path)
        logger.info(f"Importing project from {zip_path}")

        if not zip_path.exists():
            raise FileNotFoundError(f"Zip file not found: {zip_path}")

        # Extract to temporary location
        temp_dir = self.settings.temp_dir / "import_temp"
        shutil.unpack_archive(str(zip_path), str(temp_dir))

        # Find project directory
        extracted_dirs = list(temp_dir.iterdir())
        if len(extracted_dirs) != 1:
            raise ValueError("Invalid project zip file")

        extracted_project_dir = extracted_dirs[0]

        # Determine project name
        if project_name is None:
            project_name = extracted_project_dir.name

        # Check if project already exists
        if self.project_exists(project_name):
            raise ValueError(f"Project '{project_name}' already exists")

        # Move to projects directory
        target_dir = self.settings.get_project_dir(project_name)
        shutil.move(str(extracted_project_dir), str(target_dir))

        # Clean up
        shutil.rmtree(temp_dir)

        logger.success(f"Project imported as '{project_name}'")
        return project_name
