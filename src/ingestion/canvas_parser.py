"""
Obsidian Canvas file parser using PyJSONCanvas.

This module parses .canvas files and preserves the relational structure
by synthesizing natural language context headers that describe node
connections and relationships.
"""

from pathlib import Path
from typing import List, Dict, Optional, Any
import json

from pyjsoncanvas import Canvas
from loguru import logger

from llama_index.core.schema import Document

from ..config import get_settings


class ObsidianCanvasParser:
    """
    Parser for Obsidian Canvas files (.canvas).

    Transforms graph-based visual information into linear text format
    while preserving relational context through synthesized headers.
    """

    def __init__(self):
        """Initialize the canvas parser."""
        self.settings = get_settings()
        logger.info("Initialized Obsidian Canvas parser")

    def parse_canvas(self, canvas_path: Path | str) -> List[Document]:
        """
        Parse an Obsidian Canvas file into LlamaIndex Documents.

        Each node in the canvas becomes a separate document with
        context about its connections.

        Args:
            canvas_path: Path to .canvas file

        Returns:
            List of LlamaIndex Documents, one per canvas node
        """
        canvas_path = Path(canvas_path)
        logger.info(f"Parsing Obsidian Canvas: {canvas_path}")

        try:
            # Load canvas file
            canvas = Canvas.from_json(canvas_path)

            # Parse all nodes
            documents = []
            for node in canvas.nodes:
                doc = self._parse_node(node, canvas, canvas_path)
                if doc:
                    documents.append(doc)

            logger.success(
                f"Parsed canvas: {len(documents)} nodes extracted"
            )

            return documents

        except Exception as e:
            logger.error(f"Failed to parse canvas: {e}")
            raise

    def _parse_node(
        self,
        node: Any,
        canvas: Canvas,
        canvas_path: Path
    ) -> Optional[Document]:
        """
        Parse a single canvas node into a Document.

        Args:
            node: Canvas node object
            canvas: Parent canvas object
            canvas_path: Path to canvas file

        Returns:
            LlamaIndex Document with contextualized content
        """
        try:
            # Get node ID and type
            node_id = node.id
            node_type = node.type

            # Extract text content based on node type
            if node_type == "text":
                content = node.text
            elif node_type == "file":
                # For file nodes, note the file path
                content = f"[File Reference: {node.file}]"
            elif node_type == "link":
                # For link nodes, include the URL
                content = f"[External Link: {node.url}]"
            else:
                logger.warning(f"Unknown node type: {node_type}")
                return None

            if not content or not content.strip():
                return None

            # Get connections for this node
            connections = self._get_node_connections(node, canvas)

            # Synthesize context header
            context_header = self._synthesize_context_header(
                node=node,
                canvas_name=canvas_path.stem,
                connections=connections
            )

            # Combine context header with content
            full_text = f"{context_header}\n\n{content}"

            # Build metadata
            metadata = {
                "source_file_path": str(canvas_path.absolute()),
                "document_type": "obsidian_canvas",
                "canvas_name": canvas_path.stem,
                "node_id": node_id,
                "node_type": node_type,
                "processing_method": "pyjsoncanvas",
                "num_connections": len(connections)
            }

            # Add position data if available
            if hasattr(node, 'x') and hasattr(node, 'y'):
                metadata["canvas_position"] = {"x": node.x, "y": node.y}

            # Add color if available
            if hasattr(node, 'color'):
                metadata["node_color"] = node.color

            # Create document
            document = Document(
                text=full_text,
                metadata=metadata,
                id_=f"canvas_{canvas_path.stem}_{node_id}"
            )

            return document

        except Exception as e:
            logger.warning(f"Failed to parse node {node.id}: {e}")
            return None

    def _get_node_connections(
        self,
        node: Any,
        canvas: Canvas
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all connections (edges) for a node.

        Args:
            node: Canvas node
            canvas: Parent canvas

        Returns:
            Dictionary with 'incoming' and 'outgoing' edge lists
        """
        connections = {
            "incoming": [],
            "outgoing": []
        }

        node_id = node.id

        # Iterate through all edges in canvas
        for edge in canvas.edges:
            edge_data = {
                "edge_id": edge.id,
                "label": getattr(edge, 'label', None)
            }

            # Check if this edge connects to our node
            if edge.toNode == node_id:
                # Incoming edge
                from_node = self._find_node_by_id(canvas, edge.fromNode)
                if from_node:
                    edge_data["from_node_id"] = edge.fromNode
                    edge_data["from_node_type"] = from_node.type
                    if from_node.type == "text" and hasattr(from_node, 'text'):
                        # Get first 50 chars as preview
                        edge_data["from_node_preview"] = from_node.text[:50]
                connections["incoming"].append(edge_data)

            if edge.fromNode == node_id:
                # Outgoing edge
                to_node = self._find_node_by_id(canvas, edge.toNode)
                if to_node:
                    edge_data["to_node_id"] = edge.toNode
                    edge_data["to_node_type"] = to_node.type
                    if to_node.type == "text" and hasattr(to_node, 'text'):
                        edge_data["to_node_preview"] = to_node.text[:50]
                connections["outgoing"].append(edge_data)

        return connections

    def _find_node_by_id(self, canvas: Canvas, node_id: str) -> Optional[Any]:
        """Find a node by its ID."""
        for node in canvas.nodes:
            if node.id == node_id:
                return node
        return None

    def _synthesize_context_header(
        self,
        node: Any,
        canvas_name: str,
        connections: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Synthesize a natural language context header.

        This header describes the node's position in the canvas graph
        and its relationships to other nodes.

        Args:
            node: Canvas node
            canvas_name: Name of the canvas
            connections: Node connections

        Returns:
            Natural language context header
        """
        lines = [f"=== From Obsidian Canvas: '{canvas_name}' ==="]

        # Describe node type
        if node.type == "text":
            lines.append("This is a text note.")
        elif node.type == "file":
            lines.append(f"This references the file: {node.file}")
        elif node.type == "link":
            lines.append(f"This is a link to: {node.url}")

        # Describe incoming connections
        if connections["incoming"]:
            lines.append("\nIncoming connections:")
            for edge in connections["incoming"]:
                label = f" (labeled: '{edge['label']}')" if edge.get('label') else ""
                preview = edge.get('from_node_preview', '')
                preview_text = f": \"{preview}...\"" if preview else ""
                lines.append(
                    f"  • Connected from {edge['from_node_type']} node{label}{preview_text}"
                )

        # Describe outgoing connections
        if connections["outgoing"]:
            lines.append("\nOutgoing connections:")
            for edge in connections["outgoing"]:
                label = f" (labeled: '{edge['label']}')" if edge.get('label') else ""
                preview = edge.get('to_node_preview', '')
                preview_text = f": \"{preview}...\"" if preview else ""
                lines.append(
                    f"  • Connects to {edge['to_node_type']} node{label}{preview_text}"
                )

        # Add positioning context if isolated
        if not connections["incoming"] and not connections["outgoing"]:
            lines.append("\nThis note is standalone (no connections).")

        lines.append("=" * 50)

        return "\n".join(lines)

    def batch_parse_canvases(
        self,
        canvas_paths: List[Path | str]
    ) -> List[Document]:
        """
        Parse multiple canvas files in batch.

        Args:
            canvas_paths: List of paths to .canvas files

        Returns:
            List of all Documents from all canvases
        """
        logger.info(f"Batch parsing {len(canvas_paths)} canvas files")

        all_documents = []
        for i, path in enumerate(canvas_paths, 1):
            logger.info(f"Parsing canvas {i}/{len(canvas_paths)}: {path}")
            try:
                docs = self.parse_canvas(path)
                all_documents.extend(docs)
            except Exception as e:
                logger.error(f"Failed to parse {path}: {e}")
                continue

        logger.success(
            f"Batch parsing complete: {len(all_documents)} total documents"
        )
        return all_documents

    def visualize_canvas_structure(self, canvas_path: Path | str) -> str:
        """
        Create a text visualization of the canvas structure.

        Useful for debugging and understanding canvas organization.

        Args:
            canvas_path: Path to .canvas file

        Returns:
            Text visualization of canvas structure
        """
        canvas_path = Path(canvas_path)
        canvas = Canvas.from_json(canvas_path)

        lines = [
            f"Canvas: {canvas_path.stem}",
            f"Nodes: {len(canvas.nodes)}",
            f"Edges: {len(canvas.edges)}",
            "\n--- Node Structure ---"
        ]

        for i, node in enumerate(canvas.nodes, 1):
            connections = self._get_node_connections(node, canvas)
            in_count = len(connections["incoming"])
            out_count = len(connections["outgoing"])

            lines.append(
                f"\n{i}. {node.type.upper()} (ID: {node.id})"
            )
            lines.append(f"   Incoming: {in_count}, Outgoing: {out_count}")

            if node.type == "text" and hasattr(node, 'text'):
                preview = node.text[:80].replace('\n', ' ')
                lines.append(f"   Preview: {preview}...")

        return "\n".join(lines)
