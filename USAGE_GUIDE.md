# RAG Corpus - Complete Usage Guide

## Table of Contents
1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Creating Your First Project](#creating-your-first-project)
4. [Ingesting Documents](#ingesting-documents)
5. [Using the Chat Interface](#using-the-chat-interface)
6. [Advanced Features](#advanced-features)
7. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Tesseract OCR
- (Optional) PostgreSQL for chat history
- (Optional) Ollama for local LLM

### Step 1: Install Dependencies

```bash
# Clone repository
cd RAGCorpus

# Install Python packages
pip install -e .

# Or with development tools
pip install -e ".[dev]"
```

### Step 2: Install Tesseract

**Windows:**
```bash
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
# Install to default location: C:\Program Files\Tesseract-OCR
```

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # For German support
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-deu  # For German
```

### Step 3: (Optional) Install Ollama

```bash
# Download from https://ollama.ai
# Pull a model
ollama pull llama3.1:8b
```

---

## Configuration

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Edit .env File

**Required Settings:**

```bash
# Choose your LLM provider
DEFAULT_LLM_PROVIDER=gemini  # or 'ollama'

# If using Gemini
GOOGLE_API_KEY=your_api_key_here

# If using Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

**Optional Settings:**

```bash
# Zotero (optional)
ZOTERO_USER_ID=your_user_id
ZOTERO_API_KEY=your_api_key

# Web search (optional)
TAVILY_API_KEY=your_tavily_key

# Database for chat history (optional)
DATABASE_URL=postgresql://user:pass@localhost/ragcorpus
```

### 3. Adjust Performance Settings

```bash
# For smaller machines
CHUNK_SIZE=256
TOP_K_RETRIEVAL=5
RERANK_TOP_N=2

# For larger machines
CHUNK_SIZE=512
TOP_K_RETRIEVAL=10
RERANK_TOP_N=3
```

---

## Creating Your First Project

### Method 1: Using the Ingestion Script

```bash
python scripts/ingest_corpus.py
```

Follow the prompts:
1. Enter project name: `my_research`
2. Enter description: `My Dewey and Gestalt research`
3. Enter corpus path: `/path/to/your/documents`

### Method 2: Using Python

```python
from src.storage import ProjectManager, VectorStoreManager
from src.ingestion import DocumentPipeline

# Create project
pm = ProjectManager()
pm.create_project(
    "my_research",
    description="My Dewey and Gestalt research"
)

# Initialize pipeline and vector store
pipeline = DocumentPipeline("my_research")
vector_store = VectorStoreManager("my_research")

# Ingest documents
storage_context = vector_store.get_storage_context()
index = pipeline.ingest_and_index(
    source="/path/to/documents",
    is_directory=True,
    storage_context=storage_context
)

print("✅ Project created and documents indexed!")
```

---

## Ingesting Documents

### Supported File Types

The system automatically detects and processes:

| File Type | Processing Method |
|-----------|------------------|
| Clean PDFs | SimpleDirectoryReader |
| Scanned PDFs | OCR with OpenCV + Tesseract |
| German texts (.txt, .pdf) | MarianMT translation |
| Obsidian Canvas (.canvas) | Graph structure preservation |
| Markdown (.md) | Direct ingestion |
| Text files (.txt) | Direct ingestion |

### Ingesting a Directory

```python
from src.ingestion import DocumentPipeline, DocumentType

pipeline = DocumentPipeline("my_project")

# Automatic detection
documents = pipeline.ingest_directory(
    "/path/to/corpus",
    recursive=True,
    file_types=['.pdf', '.txt', '.md', '.canvas']
)

# Or specify document type
documents = pipeline.ingest_directory(
    "/path/to/scanned_books",
    document_type=DocumentType.SCANNED_PDF
)
```

### Ingesting a Single File

```python
# Single file with auto-detection
docs = pipeline.ingest_file("/path/to/document.pdf")

# German text with translation
docs = pipeline.ingest_file(
    "/path/to/german_text.txt",
    document_type=DocumentType.GERMAN_TEXT
)

# Obsidian Canvas
docs = pipeline.ingest_file(
    "/path/to/mindmap.canvas",
    document_type=DocumentType.OBSIDIAN_CANVAS
)
```

### Adding Documents to Existing Project

```python
from src.storage import VectorStoreManager

# Load existing index
vector_store = VectorStoreManager("my_project")
index = vector_store.load_index()

# Ingest new documents
new_docs = pipeline.ingest_file("/path/to/new_paper.pdf")

# Add to index
vector_store.add_documents(index, new_docs)

print(f"Added {len(new_docs)} documents to index")
```

---

## Using the Chat Interface

### Starting the UI

```bash
chainlit run src/ui/app.py
```

This will open your browser to `http://localhost:8000`

### Chat Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/projects` | List available projects |
| `/load <name>` | Load a specific project |
| `/create <name>` | Create a new project |
| `/info` | Show current project info |

### Example Queries

**Basic Question:**
```
What does Dewey say about the relationship between inquiry and experience?
```

**Cross-Examination:**
```
Cross-examine my draft at ~/Documents/integration_paper.md
focusing on the concept of functional coordination
```

**Zotero Search:**
```
What papers do I have in Zotero by Wolfgang Köhler from the 1920s?
```

**Find Paper:**
```
Find and add the paper with DOI 10.1037/h0074428
```

**Follow-up Question:**
```
Can you elaborate on the third point about perceptual organization?
```

---

## Advanced Features

### 1. OCR Enhancement with LLM

Improve OCR quality using LLM post-processing:

```python
from src.ingestion import OCRProcessor
from llama_index.core import Settings

ocr = OCRProcessor()

# Process PDF
document = ocr.process_pdf("scanned_book.pdf")

# Enhance with LLM
enhanced_text = ocr.enhance_with_llm(
    document.text,
    llm_client=Settings.llm
)

document.text = enhanced_text
```

### 2. Custom Metadata

Add custom metadata for advanced filtering:

```python
documents = pipeline.ingest_directory("/path/to/corpus")

# Add custom metadata
pipeline.add_custom_metadata(documents, {
    "author": "John Dewey",
    "topic": "Logic",
    "decade": "1930s",
    "collection": "Collected Works Vol 12"
})
```

### 3. Project Export/Import

```python
from src.storage import ProjectManager

pm = ProjectManager()

# Export project
pm.export_project("my_research", "/backups/my_research.zip")

# Import project
new_name = pm.import_project("/backups/my_research.zip", "restored_research")
```

### 4. Retrieval Debugging

```python
from src.retrieval import HybridRetriever

# Create retriever
retriever = HybridRetriever(index)

# Explain retrieval
explanation = retriever.explain_retrieval(
    "What is the role of integration in Dewey's theory?"
)

print(f"Vector results: {explanation['vector_results']}")
print(f"BM25 results: {explanation['bm25_results']}")
print(f"Fused results: {explanation['fused_results']}")
```

### 5. Canvas Visualization

```python
from src.ingestion import ObsidianCanvasParser

parser = ObsidianCanvasParser()

# Get visual structure
structure = parser.visualize_canvas_structure("/path/to/mindmap.canvas")
print(structure)
```

---

## Troubleshooting

### Common Issues

**1. "Tesseract not found" Error**

```bash
# Windows: Add to PATH or set in .env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Linux/Mac: Install via package manager
brew install tesseract  # macOS
sudo apt-get install tesseract-ocr  # Ubuntu
```

**2. "CUDA out of memory" Error**

Reduce batch sizes and chunk sizes:
```bash
# In .env
CHUNK_SIZE=256
TRANSLATION_BATCH_SIZE=4
RERANK_TOP_N=2
```

**3. "No module named cv2" Error**

```bash
pip install opencv-python
```

**4. Slow Embedding Generation**

Use smaller embedding model:
```bash
# In .env
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

**5. Gemini API Rate Limits**

Switch to Ollama for unlimited local inference:
```bash
# In .env
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1:8b
```

### Performance Optimization

**For Low-Memory Systems:**
```python
# settings adjustment
settings.chunk_size = 256
settings.top_k_retrieval = 5
settings.rerank_top_n = 2
```

**For Fast Ingestion:**
```python
# Process in batches
for batch in batches_of_files:
    documents = pipeline.ingest_directory(batch)
    vector_store.add_documents(index, documents)
```

### Getting Help

1. Check logs: `~/.ragcorpus/logs/`
2. Enable debug logging:
   ```python
   from loguru import logger
   logger.add("debug.log", level="DEBUG")
   ```
3. File an issue on GitHub

---

## Next Steps

- Read the [InitialInstructions.md](InitialInstructions.md) for architectural details
- Explore the [README.md](README.md) for feature overview
- Check the `examples/` directory for code samples
- Join the community discussions

Happy researching! 🎓
