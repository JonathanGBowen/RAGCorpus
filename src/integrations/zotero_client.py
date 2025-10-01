"""
Zotero integration using PyZotero.

Provides access to user's Zotero library for citation management
and reference lookup.
"""

from typing import List, Dict, Any, Optional

from pyzotero import zotero
from langchain.tools import Tool
from loguru import logger

from ..config import get_settings


class ZoteroIntegration:
    """
    Integration with Zotero reference manager.

    Allows querying and retrieving citations from a Zotero library.
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        library_type: str = "user"
    ):
        """
        Initialize Zotero client.

        Args:
            user_id: Zotero user ID (from settings if None)
            api_key: Zotero API key (from settings if None)
            library_type: 'user' or 'group'
        """
        settings = get_settings()

        self.user_id = user_id or settings.zotero_user_id
        self.api_key = api_key or settings.zotero_api_key
        self.library_type = library_type

        if not self.user_id or not self.api_key:
            raise ValueError(
                "Zotero credentials not configured. "
                "Set ZOTERO_USER_ID and ZOTERO_API_KEY in .env"
            )

        logger.info(f"Initializing Zotero client for {library_type} library")

        # Create Zotero client
        self.zot = zotero.Zotero(
            library_id=self.user_id,
            library_type=self.library_type,
            api_key=self.api_key
        )

        logger.success("Zotero client initialized")

    def search_items(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search items in Zotero library.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of item dictionaries
        """
        logger.debug(f"Searching Zotero: {query}")

        try:
            items = self.zot.items(q=query, limit=limit)
            logger.debug(f"Found {len(items)} items")
            return items

        except Exception as e:
            logger.error(f"Zotero search failed: {e}")
            raise

    def get_item_by_key(self, item_key: str) -> Dict[str, Any]:
        """
        Get a specific item by its key.

        Args:
            item_key: Zotero item key

        Returns:
            Item dictionary
        """
        logger.debug(f"Fetching item: {item_key}")

        try:
            item = self.zot.item(item_key)
            return item

        except Exception as e:
            logger.error(f"Failed to fetch item: {e}")
            raise

    def search_by_author(
        self,
        author_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for items by author name.

        Args:
            author_name: Author name to search
            limit: Maximum results

        Returns:
            List of items by that author
        """
        logger.debug(f"Searching by author: {author_name}")

        # Search in creator field
        items = self.zot.items(q=author_name, qmode='everything', limit=limit)

        # Filter to items where author is actually in creators
        filtered = []
        for item in items:
            data = item.get('data', {})
            creators = data.get('creators', [])

            for creator in creators:
                name = f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip()
                if author_name.lower() in name.lower():
                    filtered.append(item)
                    break

        logger.debug(f"Found {len(filtered)} items by {author_name}")
        return filtered

    def search_by_year(
        self,
        year: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for items from a specific year.

        Args:
            year: Publication year
            limit: Maximum results

        Returns:
            List of items from that year
        """
        logger.debug(f"Searching by year: {year}")

        items = self.zot.items(limit=limit * 2)  # Get more to filter

        # Filter by year
        filtered = []
        for item in items:
            data = item.get('data', {})
            item_year = data.get('date', '')

            if str(year) in item_year:
                filtered.append(item)

            if len(filtered) >= limit:
                break

        logger.debug(f"Found {len(filtered)} items from {year}")
        return filtered

    def format_citation(self, item: Dict[str, Any]) -> str:
        """
        Format an item as a readable citation.

        Args:
            item: Zotero item dictionary

        Returns:
            Formatted citation string
        """
        data = item.get('data', {})

        # Extract fields
        title = data.get('title', 'No title')
        creators = data.get('creators', [])
        date = data.get('date', 'n.d.')
        publication = data.get('publicationTitle', '')
        doi = data.get('DOI', '')

        # Format authors
        author_str = ""
        if creators:
            authors = []
            for creator in creators[:3]:  # Max 3 authors
                last = creator.get('lastName', '')
                first = creator.get('firstName', '')
                if last:
                    authors.append(f"{last}, {first[0]}." if first else last)

            author_str = "; ".join(authors)
            if len(creators) > 3:
                author_str += " et al."

        # Build citation
        citation = f"{author_str} ({date}). {title}."
        if publication:
            citation += f" {publication}."
        if doi:
            citation += f" DOI: {doi}"

        return citation

    def format_items(self, items: List[Dict[str, Any]]) -> str:
        """
        Format multiple items as a readable list.

        Args:
            items: List of Zotero items

        Returns:
            Formatted string
        """
        if not items:
            return "No items found."

        result = f"Found {len(items)} items:\n\n"

        for i, item in enumerate(items, 1):
            citation = self.format_citation(item)
            result += f"{i}. {citation}\n\n"

        return result


def create_zotero_tool() -> Optional[Tool]:
    """
    Create a LangChain tool for Zotero integration.

    Returns:
        Zotero search Tool or None if not configured
    """
    settings = get_settings()

    if not settings.zotero_user_id or not settings.zotero_api_key:
        logger.warning("Zotero not configured, tool unavailable")
        return None

    try:
        zot = ZoteroIntegration()

        def search_zotero(query: str) -> str:
            """Search Zotero library."""
            try:
                # Parse query for special commands
                query_lower = query.lower()

                if query_lower.startswith("author:"):
                    # Search by author
                    author = query[7:].strip()
                    items = zot.search_by_author(author)
                elif query_lower.startswith("year:"):
                    # Search by year
                    year_str = query[5:].strip()
                    year = int(year_str)
                    items = zot.search_by_year(year)
                else:
                    # General search
                    items = zot.search_items(query)

                return zot.format_items(items)

            except Exception as e:
                logger.error(f"Zotero search failed: {e}")
                return f"Error searching Zotero: {str(e)}"

        return Tool(
            name="SearchZotero",
            func=search_zotero,
            description=(
                "Search your Zotero reference library for citations and papers. "
                "Input can be a general search query, or use 'author:Name' to search "
                "by author, or 'year:YYYY' to search by year. "
                "Returns formatted citations with DOI when available."
            )
        )

    except Exception as e:
        logger.warning(f"Failed to create Zotero tool: {e}")
        return None
