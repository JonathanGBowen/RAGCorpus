"""
Cross-encoder re-ranking for precision refinement.

This module implements a second-stage re-ranking using cross-encoder
models to improve precision after initial hybrid retrieval.
"""

from typing import List, Optional

from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.core.indices.vector_store import VectorStoreIndex
from loguru import logger

from ..config import get_settings


class CrossEncoderReranker:
    """
    Cross-encoder based re-ranker.

    Uses a cross-encoder model to re-score and re-rank nodes
    based on precise query-document relevance.

    Cross-encoders are slower but more accurate than bi-encoders
    because they jointly encode the query and document.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        top_n: Optional[int] = None
    ):
        """
        Initialize the reranker.

        Args:
            model_name: Cross-encoder model name (from settings if None)
            top_n: Number of top results to return (from settings if None)
        """
        settings = get_settings()

        self.model_name = model_name or settings.reranker_model
        self.top_n = top_n or settings.rerank_top_n

        logger.info(
            f"Initializing cross-encoder reranker: {self.model_name} (top_n={self.top_n})"
        )

        # Create LlamaIndex reranker
        self.reranker = SentenceTransformerRerank(
            model=self.model_name,
            top_n=self.top_n
        )

        logger.success("Reranker initialized")

    def rerank(
        self,
        query: str,
        nodes: List[NodeWithScore]
    ) -> List[NodeWithScore]:
        """
        Re-rank nodes based on query relevance.

        Args:
            query: Query string
            nodes: List of nodes to re-rank

        Returns:
            Re-ranked list of nodes (limited to top_n)
        """
        if not nodes:
            return nodes

        logger.debug(f"Re-ranking {len(nodes)} nodes")

        # Create query bundle
        query_bundle = QueryBundle(query_str=query)

        # Re-rank using cross-encoder
        reranked_nodes = self.reranker.postprocess_nodes(
            nodes=nodes,
            query_bundle=query_bundle
        )

        logger.debug(
            f"Re-ranking complete: {len(nodes)} -> {len(reranked_nodes)} nodes"
        )

        return reranked_nodes

    def get_postprocessor(self) -> SentenceTransformerRerank:
        """
        Get the underlying LlamaIndex postprocessor.

        This can be used directly in query engine configuration.

        Returns:
            SentenceTransformerRerank instance
        """
        return self.reranker

    def explain_reranking(
        self,
        query: str,
        nodes: List[NodeWithScore]
    ) -> dict:
        """
        Explain the re-ranking process with before/after comparison.

        Args:
            query: Query string
            nodes: List of nodes to re-rank

        Returns:
            Dictionary with re-ranking explanation
        """
        if not nodes:
            return {"error": "No nodes to rerank"}

        # Store original scores and order
        original = [
            {
                "rank": i + 1,
                "text": node.node.get_content()[:200],
                "original_score": node.score,
                "node_id": node.node.node_id
            }
            for i, node in enumerate(nodes)
        ]

        # Re-rank
        reranked_nodes = self.rerank(query, nodes)

        # Build new order
        reranked = [
            {
                "rank": i + 1,
                "text": node.node.get_content()[:200],
                "rerank_score": node.score,
                "node_id": node.node.node_id
            }
            for i, node in enumerate(reranked_nodes)
        ]

        explanation = {
            "query": query,
            "num_input_nodes": len(nodes),
            "num_output_nodes": len(reranked_nodes),
            "original_top_5": original[:5],
            "reranked_top_5": reranked[:5],
            "model": self.model_name
        }

        return explanation


def create_reranker(top_n: Optional[int] = None) -> CrossEncoderReranker:
    """
    Factory function to create a reranker with default settings.

    Args:
        top_n: Number of top results (from settings if None)

    Returns:
        CrossEncoderReranker instance
    """
    return CrossEncoderReranker(top_n=top_n)


def create_query_engine_with_reranking(
    index: VectorStoreIndex,
    retriever,
    top_n: Optional[int] = None
) -> BaseQueryEngine:
    """
    Create a query engine with hybrid retrieval and re-ranking.

    Args:
        index: VectorStoreIndex
        retriever: Hybrid retriever instance
        top_n: Number of results after re-ranking

    Returns:
        BaseQueryEngine with full pipeline
    """
    logger.info("Creating query engine with hybrid retrieval and re-ranking")

    # Create reranker
    reranker = create_reranker(top_n)

    # Create query engine
    query_engine = index.as_query_engine(
        retriever=retriever.get_retriever(),
        node_postprocessors=[reranker.get_postprocessor()]
    )

    logger.success("Query engine created with full retrieval pipeline")

    return query_engine
