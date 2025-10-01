"""External integrations for Zotero and paper retrieval."""

from .zotero_client import ZoteroIntegration, create_zotero_tool
from .paper_finder import PaperFinder, create_paper_finder_tool

__all__ = [
    "ZoteroIntegration",
    "create_zotero_tool",
    "PaperFinder",
    "create_paper_finder_tool"
]
