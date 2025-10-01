"""
Automatic paper finding and ingestion using paperscraper and Unpaywall.

Finds open-access versions of academic papers and ingests them into
the knowledge base.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import requests

from langchain.tools import Tool
from loguru import logger

from ..config import get_settings


class PaperFinder:
    """
    Finds and downloads open-access academic papers.

    Uses multiple sources:
    1. paperscraper for preprint servers (arXiv, PubMed, etc.)
    2. Unpaywall API for open-access versions
    """

    def __init__(self, download_dir: Optional[Path] = None):
        """
        Initialize paper finder.

        Args:
            download_dir: Directory to save PDFs (temp dir if None)
        """
        settings = get_settings()

        if download_dir is None:
            self.download_dir = settings.temp_dir / "downloaded_papers"
        else:
            self.download_dir = Path(download_dir)

        self.download_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Paper finder initialized (download dir: {self.download_dir})")

    def find_by_doi(self, doi: str) -> Optional[str]:
        """
        Find and download a paper by DOI.

        Tries Unpaywall first, then paperscraper.

        Args:
            doi: Digital Object Identifier

        Returns:
            Path to downloaded PDF or None
        """
        logger.info(f"Searching for paper with DOI: {doi}")

        # Try Unpaywall first
        pdf_path = self._try_unpaywall(doi)
        if pdf_path:
            return pdf_path

        # Try paperscraper
        pdf_path = self._try_paperscraper(doi)
        if pdf_path:
            return pdf_path

        logger.warning(f"Could not find open-access version for DOI: {doi}")
        return None

    def find_by_title(self, title: str) -> Optional[str]:
        """
        Find and download a paper by title.

        Args:
            title: Paper title

        Returns:
            Path to downloaded PDF or None
        """
        logger.info(f"Searching for paper: {title}")

        # This would use paperscraper's search functionality
        # Simplified implementation
        try:
            # paperscraper's search is primarily for preprint servers
            # A real implementation would use their search API

            logger.warning("Title-based search not yet implemented")
            return None

        except Exception as e:
            logger.error(f"Title search failed: {e}")
            return None

    def _try_unpaywall(self, doi: str) -> Optional[str]:
        """
        Try to find paper via Unpaywall API.

        Args:
            doi: DOI to search

        Returns:
            Path to downloaded PDF or None
        """
        logger.debug(f"Trying Unpaywall for DOI: {doi}")

        try:
            # Unpaywall API endpoint
            url = f"https://api.unpaywall.org/v2/{doi}"
            params = {"email": "user@example.com"}  # Required by Unpaywall

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Check for OA version
                if data.get('is_oa'):
                    best_oa = data.get('best_oa_location')
                    if best_oa and best_oa.get('url_for_pdf'):
                        pdf_url = best_oa['url_for_pdf']

                        logger.info(f"Found OA version via Unpaywall: {pdf_url}")

                        # Download PDF
                        return self._download_pdf(pdf_url, doi)

            logger.debug("No OA version found via Unpaywall")
            return None

        except Exception as e:
            logger.debug(f"Unpaywall search failed: {e}")
            return None

    def _try_paperscraper(self, doi: str) -> Optional[str]:
        """
        Try to find paper via paperscraper.

        Args:
            doi: DOI to search

        Returns:
            Path to downloaded PDF or None
        """
        logger.debug(f"Trying paperscraper for DOI: {doi}")

        try:
            # paperscraper integration
            # Note: paperscraper API varies by version
            # This is a simplified example

            # from paperscraper.pdf import save_pdf
            # paper_data = {"doi": doi}
            # save_pdf(paper_data, filepath=str(self.download_dir))

            logger.warning("paperscraper integration not fully implemented")
            return None

        except Exception as e:
            logger.debug(f"paperscraper search failed: {e}")
            return None

    def _download_pdf(self, url: str, identifier: str) -> Optional[str]:
        """
        Download a PDF from URL.

        Args:
            url: PDF URL
            identifier: Identifier for filename (e.g., DOI)

        Returns:
            Path to downloaded file or None
        """
        logger.debug(f"Downloading PDF from: {url}")

        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Create filename
            safe_id = identifier.replace('/', '_').replace(':', '_')
            filename = f"{safe_id}.pdf"
            filepath = self.download_dir / filename

            # Save PDF
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.success(f"Downloaded PDF: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"PDF download failed: {e}")
            return None

    def find_and_ingest(
        self,
        doi: str,
        pipeline,
        index
    ) -> str:
        """
        Find paper and ingest into knowledge base.

        Args:
            doi: DOI to search
            pipeline: DocumentPipeline instance
            index: VectorStoreIndex to add to

        Returns:
            Status message
        """
        logger.info(f"Finding and ingesting paper: {doi}")

        # Find PDF
        pdf_path = self.find_by_doi(doi)

        if not pdf_path:
            return f"Could not find open-access version for DOI: {doi}"

        # Ingest PDF
        try:
            documents = pipeline.ingest_file(pdf_path)

            # Add to index
            for doc in documents:
                index.insert(doc)

            logger.success(f"Successfully ingested paper: {doi}")
            return (
                f"Successfully downloaded and indexed paper with DOI: {doi}\n"
                f"File: {Path(pdf_path).name}\n"
                f"Added {len(documents)} documents to the knowledge base."
            )

        except Exception as e:
            logger.error(f"Failed to ingest paper: {e}")
            return f"Downloaded but failed to ingest: {str(e)}"


def create_paper_finder_tool(
    pipeline,
    index
) -> Tool:
    """
    Create a LangChain tool for paper finding and ingestion.

    Args:
        pipeline: DocumentPipeline instance
        index: VectorStoreIndex to add papers to

    Returns:
        Paper finder Tool
    """
    finder = PaperFinder()

    def find_and_add_paper(doi: str) -> str:
        """Find and add a paper by DOI."""
        try:
            return finder.find_and_ingest(doi, pipeline, index)
        except Exception as e:
            logger.error(f"Paper finder tool failed: {e}")
            return f"Error: {str(e)}"

    return Tool(
        name="FindAndAddPaper",
        func=find_and_add_paper,
        description=(
            "Find and download an open-access academic paper by DOI, then add it "
            "to the knowledge base. Input should be a valid DOI (e.g., '10.1007/s11229-018-02022-y'). "
            "This tool will search Unpaywall and preprint servers for free versions, "
            "download the PDF, process it, and add it to the searchable corpus."
        )
    )
