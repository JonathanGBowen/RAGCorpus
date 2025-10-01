# RAG Corpus - ADHD-Friendly Academic Research Assistant

A comprehensive Retrieval-Augmented Generation (RAG) system designed specifically for ADHD academics, featuring advanced document processing, multilingual support, and an intuitive visual interface.

## Features

### Core Capabilities
- **Advanced OCR Pipeline**: Process poorly scanned PDFs with OpenCV preprocessing and Tesseract OCR
- **Multilingual Support**: Automatic German-to-English translation using MarianMT models
- **Obsidian Integration**: Parse and contextualize Obsidian Canvas files with relationship mapping
- **Hybrid Retrieval**: Combines dense vector search with sparse BM25 keyword matching
- **Cross-Encoder Re-ranking**: Precision re-ranking using BAAI/bge-reranker for maximum relevance
- **Agentic Framework**: LangGraph-powered ReAct agent with memory and multi-step reasoning

### Advanced Tools
- **Cross-Examination**: Compare drafts against the research library with parallel retrieval
- **Zotero Integration**: Query and manage your Zotero reference library
- **Auto-Scour**: Automatically find and ingest open-access papers using DOI
- **Web Search**: Fallback to web search for information not in the corpus

### ADHD-Friendly Design
- Minimalistic, distraction-free UI with Chainlit
- Visual agent step display to reduce cognitive load
- Clear source attribution and metadata
- Project-based organization for context management
- Dark mode support

## Architecture

### Tech Stack
- **LlamaIndex**: Document ingestion and indexing pipeline
- **ChromaDB**: Local-first vector storage with persistence
- **LangGraph**: Agentic workflow orchestration
- **Chainlit**: Chat-based user interface
- **Gemini/Ollama**: LLM providers
- **BAAI/bge-m3**: Multilingual embedding model

### Project Structure
```
RAGCorpus/
├── src/
│   ├── config/          # Configuration and settings
│   ├── ingestion/       # Document loading and preprocessing
│   ├── retrieval/       # Hybrid search and re-ranking
│   ├── agent/           # LangGraph agent and tools
│   ├── integrations/    # Zotero, paperscraper, web search
│   ├── storage/         # Vector store and project management
│   └── ui/              # Chainlit application
├── data/
│   └── projects/        # Project-specific data and indices
└── tests/               # Test suite
```

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd RAGCorpus
```

2. **Install dependencies**:
```bash
pip install -e .
```

3. **Install Tesseract OCR**:
   - Windows: Download from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)
   - macOS: `brew install tesseract`
   - Linux: `sudo apt-get install tesseract-ocr`

4. **Install German language pack for Tesseract**:
```bash
# Download German training data
# Windows: Place in C:\Program Files\Tesseract-OCR\tessdata\
# Linux/Mac: Usually in /usr/share/tesseract-ocr/4.00/tessdata/
```

5. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

6. **Database for chat history**:
   - **SQLite** (default): Already configured - no setup needed! ✅
   - **PostgreSQL** (optional): See [docs/DATABASE_SETUP.md](docs/DATABASE_SETUP.md) for migration

## Quick Start

### 1. Ingest Documents

```python
from src.ingestion.pipeline import DocumentPipeline

pipeline = DocumentPipeline(project_name="my_research")
pipeline.ingest_directory("path/to/your/documents")
```

### 2. Launch the UI

```bash
chainlit run src/ui/app.py
```

### 3. Start Researching

Open your browser to `http://localhost:8000` and start asking questions!

## Usage Examples

### Basic Query
```
User: What does Dewey say about the concept of integration in inquiry?
Assistant: [Searches corpus, retrieves relevant passages, provides answer with sources]
```

### Cross-Examination
```
User: Cross-examine my draft at ~/drafts/integration_paper.md against the library,
      focusing on the relationship between integration and functional coordination.
Assistant: [Analyzes draft, compares with library, identifies synergies and gaps]
```

### Zotero Integration
```
User: What papers do I have in Zotero about Gestalt psychology from the 1930s?
Assistant: [Queries Zotero library, returns formatted citations]
```

### Auto-Scour
```
User: Find and add the paper with DOI 10.1007/s11229-018-02022-y to my library
Assistant: [Downloads paper, processes it, adds to vector store]
```

## Document Processing

### Supported Formats
- Clean PDFs and text files
- Poorly scanned/image-based PDFs (with OCR)
- German language documents (with translation)
- Obsidian Canvas files (.canvas)
- Markdown and personal notes

### OCR Preprocessing Pipeline
1. **Rescaling**: Upscale to 300 DPI
2. **Grayscale & Adaptive Binarization**: Handle uneven lighting
3. **Deskewing**: Correct page rotation
4. **Noise Removal**: Filter digital artifacts
5. **Tesseract OCR**: Extract text with German language support

## Project Management

Create isolated research contexts with separate indices and chat histories:

```python
# Create new project
create_project("dewey_integration")

# Load existing project
load_project("gestalt_perception")

# Projects are automatically saved
```

## Configuration

Edit `.env` to customize:
- LLM provider (Gemini or Ollama)
- Embedding and re-ranking models
- Chunk size and overlap
- Retrieval parameters
- API keys

## Development

### Run Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
ruff check src/
```

### Type Checking
```bash
mypy src/
```

## Troubleshooting

### OCR Issues
- Ensure Tesseract is installed and in PATH
- Install German language pack for German texts
- Adjust OpenCV preprocessing parameters in `src/config/settings.py`

### Memory Issues
- Reduce chunk size or top_k retrieval parameters
- Use Ollama with smaller models (e.g., 7B instead of 13B)
- Process documents in smaller batches

### UI Not Loading
- Check Chainlit installation: `pip install chainlit --upgrade`
- Ensure port 8000 is available
- Check logs for API key issues

## Contributing

Contributions welcome! Please:
1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Use Black for formatting

## License

[Your chosen license]

## Citations

This system implements techniques from:
- LlamaIndex Documentation
- LangChain/LangGraph Documentation
- BAAI BGE Model Papers
- Chainlit Documentation
- Research on RAG systems and cognitive accessibility

## Acknowledgments

Built for ADHD academics who need powerful, distraction-free research tools.
