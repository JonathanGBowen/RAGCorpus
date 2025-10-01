"""
Hybrid retrieval combining dense vector search with sparse BM25.

This module implements the QueryFusionRetriever pattern, combining
the semantic power of vector embeddings with the lexical precision
of keyword-based BM25 search.
"""

from typing import List, Optional

from llama_index.core import VectorStoreIndex, QueryBundle
from llama_index.core.retrievers import (
    BaseRetriever,
    QueryFusionRetriever,
    VectorIndexRetriever
)
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.schema import NodeWithScore, TextNode
from loguru import logger

from ..config import get_settings


class HybridRetriever:
    """
    Hybrid retriever combining dense and sparse retrieval.

    Uses QueryFusionRetriever to fuse results from:
    1. Dense retrieval: Vector similarity search (semantic)
    2. Sparse retrieval: BM25 keyword search (lexical)

    This provides both conceptual understanding and exact-match capability.
    """

    def __init__(
        self,
        index: VectorStoreIndex,
        vector_top_k: int = 5,
        bm25_top_k: int = 5,
        fusion_top_k: int = 10,
        mode: str = "reciprocal_rerank"
    ):
        """
        Initialize hybrid retriever.

        Args:
            index: VectorStoreIndex to retrieve from
            vector_top_k: Number of results from vector search
            bm25_top_k: Number of results from BM25 search
            fusion_top_k: Total number of results after fusion
            mode: Fusion mode ('reciprocal_rerank' or 'simple')
        """
        settings = get_settings()

        self.index = index
        self.vector_top_k = vector_top_k
        self.bm25_top_k = bm25_top_k
        self.fusion_top_k = fusion_top_k
        self.mode = mode

        logger.info(
            f"Initializing hybrid retriever "
            f"(vector_k={vector_top_k}, bm25_k={bm25_top_k}, fusion_k={fusion_top_k})"
        )

        # Create dense retriever (vector search)
        self.vector_retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=vector_top_k
        )

        # Get all nodes for BM25
        # This is needed because BM25 needs access to all documents
        self.nodes = self._get_all_nodes()

        # Create sparse retriever (BM25)
        self.bm25_retriever = BM25Retriever.from_defaults(
            nodes=self.nodes,
            similarity_top_k=bm25_top_k
        )

        # Create fusion retriever
        self.fusion_retriever = QueryFusionRetriever(
            retrievers=[self.vector_retriever, self.bm25_retriever],
            similarity_top_k=fusion_top_k,
            num_queries=1,  # Use single query for both retrievers
            mode=mode,
            use_async=False
        )

        logger.success("Hybrid retriever initialized")

    def retrieve(self, query: str) -> List[NodeWithScore]:
        """
        Retrieve nodes using hybrid search.

        Args:
            query: Query string

        Returns:
            List of nodes with scores, ranked by relevance
        """
        logger.debug(f"Hybrid retrieval for query: {query[:100]}...")

        # Use fusion retriever
        nodes = self.fusion_retriever.retrieve(query)

        logger.debug(f"Retrieved {len(nodes)} nodes from hybrid search")

        return nodes

    def retrieve_with_scores(self, query: str) -> List[tuple[NodeWithScore, float]]:
        """
        Retrieve nodes with detailed score breakdown.

        Args:
            query: Query string

        Returns:
            List of (node, score) tuples
        """
        nodes = self.retrieve(query)
        return [(node, node.score if node.score is not None else 0.0) for node in nodes]

    def explain_retrieval(self, query: str) -> dict:
        """
        Retrieve and explain the retrieval process.

        Useful for debugging and understanding retrieval quality.

        Args:
            query: Query string

        Returns:
            Dictionary with retrieval explanation
        """
        logger.debug(f"Explaining retrieval for: {query[:100]}...")

        # Get vector-only results
        vector_nodes = self.vector_retriever.retrieve(query)

        # Get BM25-only results
        bm25_nodes = self.bm25_retriever.retrieve(query)

        # Get fused results
        fused_nodes = self.fusion_retriever.retrieve(query)

        explanation = {
            "query": query,
            "vector_results": len(vector_nodes),
            "bm25_results": len(bm25_nodes),
            "fused_results": len(fused_nodes),
            "vector_top_5": [
                {
                    "text": node.node.get_content()[:200],
                    "score": node.score
                }
                for node in vector_nodes[:5]
            ],
            "bm25_top_5": [
                {
                    "text": node.node.get_content()[:200],
                    "score": node.score
                }
                for node in bm25_nodes[:5]
            ],
            "fused_top_5": [
                {
                    "text": node.node.get_content()[:200],
                    "score": node.score
                }
                for node in fused_nodes[:5]
            ]
        }

        return explanation

    def _get_all_nodes(self) -> List[TextNode]:
        """
        Get all nodes from the index for BM25.

        Returns:
            List of all TextNode objects
        """
        # Retrieve nodes from the docstore
        docstore = self.index.docstore
        nodes = list(docstore.docs.values())

        logger.debug(f"Retrieved {len(nodes)} nodes for BM25 index")
        return nodes

    def update_bm25_index(self) -> None:
        """
        Update BM25 index with latest nodes.

        Call this after adding new documents to the index.
        """
        logger.info("Updating BM25 index with latest nodes")

        self.nodes = self._get_all_nodes()

        self.bm25_retriever = BM25Retriever.from_defaults(
            nodes=self.nodes,
            similarity_top_k=self.bm25_top_k
        )

        # Recreate fusion retriever
        self.fusion_retriever = QueryFusionRetriever(
            retrievers=[self.vector_retriever, self.bm25_retriever],
            similarity_top_k=self.fusion_top_k,
            num_queries=1,
            mode=self.mode,
            use_async=False
        )

        logger.success("BM25 index updated")

    def get_retriever(self) -> BaseRetriever:
        """
        Get the underlying fusion retriever.

        Returns:
            QueryFusionRetriever instance
        """
        return self.fusion_retriever


def create_hybrid_retriever(
    index: VectorStoreIndex,
    top_k: Optional[int] = None
) -> HybridRetriever:
    """
    Factory function to create a hybrid retriever with default settings.

    Args:
        index: VectorStoreIndex to retrieve from
        top_k: Total number of results (from settings if None)

    Returns:
        HybridRetriever instance
    """
    settings = get_settings()
    top_k = top_k or settings.top_k_retrieval

    # Split top_k between vector and BM25
    vector_k = top_k // 2
    bm25_k = top_k // 2

    return HybridRetriever(
        index=index,
        vector_top_k=vector_k,
        bm25_top_k=bm25_k,
        fusion_top_k=top_k,
        mode="reciprocal_rerank"
    )
