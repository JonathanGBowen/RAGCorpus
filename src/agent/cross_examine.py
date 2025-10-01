"""
Cross-examination tool for comparing drafts against the research library.

This implements the advanced workflow for parallel retrieval and comparative
analysis between a user's draft and the main corpus.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import asyncio

from langchain.tools import Tool
from loguru import logger

from llama_index.core import VectorStoreIndex, Document, SummaryIndex
from llama_index.core.query_engine import BaseQueryEngine

from ..config import get_settings


class CrossExaminationTool:
    """
    Tool for cross-examining drafts against the research library.

    Workflow:
    1. Load user's draft into temporary index
    2. Query both draft and library in parallel
    3. Synthesize comparative analysis using LLM
    """

    def __init__(
        self,
        library_query_engine: BaseQueryEngine,
        llm_client: Optional[Any] = None
    ):
        """
        Initialize cross-examination tool.

        Args:
            library_query_engine: Query engine for main research library
            llm_client: LLM client for synthesis (optional)
        """
        self.library_qe = library_query_engine
        self.llm_client = llm_client
        self.settings = get_settings()

        logger.info("Cross-examination tool initialized")

    def cross_examine(
        self,
        draft_path: str,
        focus_concept: Optional[str] = None
    ) -> str:
        """
        Cross-examine a draft against the research library.

        Args:
            draft_path: Path to draft file
            focus_concept: Optional concept to focus analysis on

        Returns:
            Comparative analysis text
        """
        logger.info(f"Cross-examining draft: {draft_path}")

        try:
            # Step 1: Load draft
            draft_doc = self._load_draft(draft_path)

            # Step 2: Create temporary index for draft
            draft_index = self._create_draft_index(draft_doc)

            # Step 3: Formulate queries
            if focus_concept:
                draft_query = f"What does this draft say about {focus_concept}?"
                library_query = f"What does the research library say about {focus_concept}?"
            else:
                draft_query = "What are the main arguments and concepts in this draft?"
                library_query = "What are the relevant concepts and arguments from the research library?"

            # Step 4: Query both sources (could be parallel)
            logger.debug("Querying draft...")
            draft_qe = draft_index.as_query_engine()
            draft_response = draft_qe.query(draft_query)

            logger.debug("Querying library...")
            library_response = self.library_qe.query(library_query)

            # Step 5: Synthesize comparative analysis
            analysis = self._synthesize_analysis(
                draft_text=str(draft_response),
                library_text=str(library_response),
                focus_concept=focus_concept,
                draft_sources=getattr(draft_response, 'source_nodes', []),
                library_sources=getattr(library_response, 'source_nodes', [])
            )

            logger.success("Cross-examination complete")
            return analysis

        except Exception as e:
            logger.error(f"Cross-examination failed: {e}")
            return f"Error during cross-examination: {str(e)}"

    def _load_draft(self, draft_path: str) -> Document:
        """
        Load draft file as a Document.

        Args:
            draft_path: Path to draft

        Returns:
            LlamaIndex Document
        """
        path = Path(draft_path).expanduser()

        if not path.exists():
            raise FileNotFoundError(f"Draft not found: {draft_path}")

        logger.debug(f"Loading draft from: {path}")

        # Read file
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()

        # Create document
        doc = Document(
            text=text,
            metadata={
                "source_file_path": str(path),
                "document_type": "user_draft",
                "filename": path.name
            },
            id_=f"draft_{path.stem}"
        )

        return doc

    def _create_draft_index(self, draft_doc: Document) -> VectorStoreIndex:
        """
        Create a temporary in-memory index for the draft.

        Args:
            draft_doc: Draft document

        Returns:
            VectorStoreIndex
        """
        logger.debug("Creating temporary draft index")

        # Create in-memory index (no persistence)
        index = VectorStoreIndex.from_documents(
            [draft_doc],
            show_progress=False
        )

        return index

    def _synthesize_analysis(
        self,
        draft_text: str,
        library_text: str,
        focus_concept: Optional[str],
        draft_sources: list,
        library_sources: list
    ) -> str:
        """
        Synthesize comparative analysis using LLM.

        Args:
            draft_text: Summary from draft
            library_text: Summary from library
            focus_concept: Concept of focus
            draft_sources: Source nodes from draft
            library_sources: Source nodes from library

        Returns:
            Comparative analysis
        """
        logger.debug("Synthesizing comparative analysis")

        # Build analysis prompt
        prompt = self._build_analysis_prompt(
            draft_text=draft_text,
            library_text=library_text,
            focus_concept=focus_concept
        )

        # Use LLM if available
        if self.llm_client:
            try:
                analysis = self.llm_client.complete(prompt).text
            except Exception as e:
                logger.warning(f"LLM synthesis failed: {e}")
                analysis = self._fallback_analysis(draft_text, library_text)
        else:
            analysis = self._fallback_analysis(draft_text, library_text)

        # Add source citations
        analysis += "\n\n" + self._format_sources(library_sources)

        return analysis

    def _build_analysis_prompt(
        self,
        draft_text: str,
        library_text: str,
        focus_concept: Optional[str]
    ) -> str:
        """Build the synthesis prompt for the LLM."""

        concept_text = f" focusing on the concept of '{focus_concept}'" if focus_concept else ""

        prompt = f"""You are an expert academic research assistant specializing in philosophical analysis.

You have been provided with two sets of information{concept_text}:

=== SET A: From the User's Draft ===
{draft_text}

=== SET B: From the Research Library ===
{library_text}

Your task is to perform a rigorous comparative analysis. In your response, you must:

1. **Identify key points of synergy and agreement** between the user's draft and the research library.

2. **Highlight any points of contradiction, tension, or significant divergence** in argumentation.

3. **Suggest specific areas** where the user's draft could be strengthened, nuanced, or expanded by incorporating concepts from the research library.

4. **Provide direct quotes or specific references** from Set B to support your suggestions.

5. **Note any gaps** in the draft where important perspectives from the library are missing.

Please structure your analysis clearly with these sections, and be specific and actionable in your recommendations.

Analysis:"""

        return prompt

    def _fallback_analysis(self, draft_text: str, library_text: str) -> str:
        """Simple fallback analysis when LLM is unavailable."""

        return f"""## Comparative Analysis

### From Your Draft:
{draft_text}

### From the Research Library:
{library_text}

### Recommendation:
Compare these two sets of information to identify:
- Areas of alignment and support for your arguments
- Concepts from the library that could strengthen your draft
- Potential contradictions to address
- Missing perspectives worth incorporating
"""

    def _format_sources(self, sources: list) -> str:
        """Format source citations."""

        if not sources:
            return ""

        result = "--- Relevant Sources from Library ---\n"

        for i, node in enumerate(sources[:5], 1):
            metadata = node.node.metadata
            source = metadata.get('source_file_path', 'Unknown')
            page = metadata.get('source_page_number', 'N/A')
            result += f"\n{i}. {Path(source).name} (Page {page})"

        return result


def create_cross_examine_tool(
    library_query_engine: BaseQueryEngine,
    llm_client: Optional[Any] = None
) -> Tool:
    """
    Create a LangChain tool for cross-examination.

    Args:
        library_query_engine: Query engine for research library
        llm_client: Optional LLM client for synthesis

    Returns:
        Cross-examination Tool
    """
    cross_examiner = CrossExaminationTool(library_query_engine, llm_client)

    def cross_examine(input_str: str) -> str:
        """
        Cross-examine a draft.

        Input format: "path/to/draft.md [concept:optional_focus_concept]"
        """
        try:
            # Parse input
            parts = input_str.split("concept:")
            draft_path = parts[0].strip()
            focus_concept = parts[1].strip() if len(parts) > 1 else None

            # Run cross-examination
            return cross_examiner.cross_examine(draft_path, focus_concept)

        except Exception as e:
            logger.error(f"Cross-examination tool failed: {e}")
            return f"Error: {str(e)}"

    return Tool(
        name="CrossExamineDraft",
        func=cross_examine,
        description=(
            "Compare a draft document against the research library to find "
            "synergies, contradictions, and areas for improvement. "
            "Input format: 'path/to/draft.md' or 'path/to/draft.md concept:focus_concept'. "
            "Returns a detailed comparative analysis with suggestions and source citations."
        )
    )
