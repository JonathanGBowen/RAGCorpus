# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG Corpus is an ADHD-friendly academic research assistant built with LlamaIndex, LangGraph, and Chainlit. It provides advanced RAG capabilities for querying academic documents with OCR, translation, and intelligent agentic workflows.

**Tech Stack:**
- LlamaIndex for document ingestion and indexing
- ChromaDB for vector storage (local-first)
- LangGraph for agentic ReAct workflows
- Chainlit for the chat UI
- Gemini/Ollama for LLM providers
- BAAI/bge-m3 for multilingual embeddings

## Essential Commands

### Setup and Installation
```bash
# Install dependencies
pip install -e .

# With development tools
pip install -e ".[dev]"

# Verify system
python scripts/test_system.py
```

### Running the Application
```bash
# Launch the chat UI (main entry point)
chainlit run src/ui/app.py

# Ingest documents into a project
python scripts/ingest_corpus.py
```

### Code Quality
```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_ingestion.py

# Run with verbose output
pytest -v tests/
```

## Architecture Overview

### Document Processing Pipeline (src/ingestion/)
The ingestion system handles multiple document types through specialized processors:
- **OCRProcessor**: Processes scanned PDFs using OpenCV preprocessing + Tesseract
- **GermanTranslator**: Translates German texts using MarianMT models
- **ObsidianCanvasParser**: Parses .canvas files preserving graph structure
- **DocumentPipeline**: Orchestrates loading → transforming → chunking → indexing

**Auto-detection logic:** The pipeline automatically detects document types based on file extensions and content heuristics (see `_detect_document_type` in [pipeline.py](src/ingestion/pipeline.py))

### Retrieval System (src/retrieval/)
Implements hybrid retrieval with precision re-ranking:
- **HybridRetriever**: Combines dense vector search (bge-m3) with sparse BM25
- Uses reciprocal rank fusion to merge results
- **ReRanker**: Cross-encoder re-ranking with BAAI/bge-reranker-base for final precision

### Agentic Framework (src/agent/)
LangGraph-powered ReAct agent with multi-step reasoning:
- **graph.py**: Creates the agent with LangGraph's `create_react_agent`
- **tools.py**: Defines tools (knowledge base search, file reading, etc.)
- **cross_examine.py**: Parallel retrieval for draft cross-examination
- Memory enabled via LangGraph's `MemorySaver` checkpoint system

**Tool execution:** The agent uses ReAct pattern (Reason → Act → Observe) with conversational memory

### Storage Layer (src/storage/)
- **VectorStoreManager**: Handles ChromaDB persistence per project
- **ProjectManager**: Manages isolated research contexts with separate indices
- Each project has its own directory: `data/projects/{project_name}/`

### Configuration (src/config/)
Pydantic-based settings with .env support:
- All settings in [settings.py](src/config/settings.py) can be overridden via environment variables
- Settings include LLM config, chunking params, retrieval params, API keys

### UI Layer (src/ui/)
Chainlit application with ADHD-friendly design:
- Visual agent step display using Chainlit's `cl.Step`
- SQLite for chat history (zero-config default)
- Project switching via chat commands

## Key Implementation Patterns

### Document Ingestion
Always use `DocumentPipeline` for ingestion:
```python
from src.ingestion import DocumentPipeline
from src.storage import VectorStoreManager

pipeline = DocumentPipeline(project_name="my_project")
vector_store = VectorStoreManager("my_project")

# For new index
storage_context = vector_store.get_storage_context()
index = pipeline.ingest_and_index(source="/path", storage_context=storage_context)

# For existing index
index = vector_store.load_index()
docs = pipeline.ingest_directory("/path")
vector_store.add_documents(index, docs)
```

### Agent Creation
The agent requires a query engine and optionally index/pipeline for paper ingestion:
```python
from src.agent.graph import create_agent, create_llm

llm = create_llm()  # Uses settings to create Gemini or Ollama
query_engine = index.as_query_engine()

agent = create_agent(
    query_engine=query_engine,
    index=index,  # Optional: enables paper finder tool
    pipeline=pipeline,  # Optional: enables paper finder tool
    llm=llm,
    enable_memory=True
)
```

### Query Engine Configuration
Use hybrid retrieval + re-ranking:
```python
from src.retrieval import HybridRetriever, ReRanker

retriever = HybridRetriever(index, similarity_top_k=10)
reranker = ReRanker(top_n=3)

query_engine = index.as_query_engine(
    retriever=retriever,
    node_postprocessors=[reranker]
)
```

## Critical Implementation Notes

### LLM Provider Switching
The system supports both Gemini and Ollama. LLM creation is centralized in `src/agent/graph.py:create_llm()`. Always use this function rather than creating LLM clients directly.

### Project Isolation
Projects are completely isolated with separate vector stores and storage directories. The `ProjectManager` handles all project lifecycle operations. Never manually manipulate project directories.

### OCR Preprocessing
For scanned PDFs, OCR quality depends on OpenCV preprocessing (rescaling, binarization, deskewing). Parameters are in settings. The OCR processor can optionally enhance output with LLM post-processing.

### Memory Management
The LangGraph agent uses checkpoint-based memory via `MemorySaver`. Thread IDs must be provided for conversation continuity (see `create_agent_config` in [graph.py](src/agent/graph.py:172)).

### Chunking Strategy
Uses LlamaIndex's `SentenceSplitter` with configurable chunk_size and overlap. Default is 512 tokens with 50 token overlap. Adjust via settings for performance tuning.

## File Structure Essentials

```
src/
├── config/          # Settings with Pydantic validation
├── ingestion/       # OCR, translation, Canvas parsing, unified pipeline
├── storage/         # ChromaDB management, project management
├── retrieval/       # Hybrid retrieval, re-ranking
├── agent/           # LangGraph agent, tools, cross-examination
├── integrations/    # Zotero, paper finder (paperscraper)
└── ui/              # Chainlit app

scripts/
├── ingest_corpus.py  # CLI for document ingestion
└── test_system.py    # System verification

examples/            # Usage examples for key workflows
```

## Environment Variables

Required for Gemini:
- `GOOGLE_API_KEY`

Optional integrations:
- `ZOTERO_USER_ID` + `ZOTERO_API_KEY`
- `TAVILY_API_KEY` (web search)

For Ollama (no API key needed):
- `DEFAULT_LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_MODEL=llama3.1:8b`

Performance tuning:
- `CHUNK_SIZE` (default: 512)
- `TOP_K_RETRIEVAL` (default: 10)
- `RERANK_TOP_N` (default: 3)

## Common Development Tasks

### Adding a New Document Type
1. Create processor in `src/ingestion/` (e.g., `new_processor.py`)
2. Add enum to `DocumentType` in [pipeline.py](src/ingestion/pipeline.py:28)
3. Add detection logic to `_detect_document_type`
4. Add routing in `ingest_file`

### Adding a New Agent Tool
1. Create tool function in `src/agent/tools.py`
2. Return a LangChain `Tool` object
3. Add to tool list in `create_agent` ([graph.py](src/agent/graph.py:85))

### Modifying Retrieval Strategy
Edit `HybridRetriever` in [hybrid_retriever.py](src/retrieval/hybrid_retriever.py). The retriever combines vector and BM25 results using reciprocal rank fusion.

### Adjusting UI Behavior
The Chainlit app is in [app.py](src/ui/app.py). Use `cl.Step` for visual agent steps. Chat history is managed by Chainlit's built-in SQLite persistence.

## Dependencies

**Core RAG:**
- llama-index (v0.10+) - document loading, indexing, query engine
- chromadb (v0.4.22+) - vector storage
- langchain + langgraph - agent framework

**Document Processing:**
- opencv-python + pytesseract - OCR
- transformers + torch - translation, embeddings
- pyjsoncanvas - Canvas file parsing

**UI:**
- chainlit (v1.0+) - chat interface with SQLite

**Optional:**
- pyzotero - Zotero integration
- paperscraper - paper downloading
- tavily-python - web search

See [pyproject.toml](pyproject.toml) for complete dependency list.

## Testing Approach

Tests should cover:
- Document ingestion for each type (OCR, translation, Canvas)
- Retrieval quality (hybrid fusion, re-ranking)
- Agent tool execution
- Project isolation

When writing tests, use pytest fixtures for shared resources (settings, test projects, sample documents).

## Database

Uses SQLite by default for Chainlit chat history (`data/chainlit.db`). PostgreSQL is optional for production/multi-user setups (see docs/DATABASE_SETUP.md).

Vector storage is handled by ChromaDB with per-project persistence in `data/projects/{project_name}/chroma_db/`.
