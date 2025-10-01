# Quick Start Guide

Get your RAG system up and running in 5 minutes.

## 1. Install

```bash
# Install dependencies
pip install -e .

# Install Tesseract OCR
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract tesseract-lang
# Linux: sudo apt-get install tesseract-ocr tesseract-ocr-deu
```

## 2. Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env - Required: Add your API key
GOOGLE_API_KEY=your_key_here  # For Gemini
# OR
DEFAULT_LLM_PROVIDER=ollama   # For local Ollama
```

## 3. Test

```bash
# Verify everything works
python scripts/test_system.py
```

## 4. Ingest Documents

```bash
# Run ingestion script
python scripts/ingest_corpus.py

# Enter project name: my_research
# Enter description: My academic research
# Enter corpus path: /path/to/your/documents
```

## 5. Launch UI

```bash
# Start Chainlit interface
chainlit run src/ui/app.py
```

Open browser to http://localhost:8000

## 6. Start Researching!

**Try these queries:**

```
What does Dewey say about inquiry and experience?

Cross-examine my draft at ~/Documents/paper.md

What papers do I have in Zotero by Koffka?

Find and add paper with DOI 10.1037/h0074428
```

---

## Project Structure

```
RAGCorpus/
├── src/                    # Core source code
│   ├── config/            # Configuration
│   ├── ingestion/         # Document processing
│   ├── retrieval/         # Hybrid search
│   ├── agent/             # LangGraph agent
│   ├── integrations/      # Zotero, papers
│   ├── storage/           # Vector store
│   └── ui/                # Chainlit UI
├── scripts/               # Utility scripts
│   ├── ingest_corpus.py   # Document ingestion
│   └── test_system.py     # System tests
├── examples/              # Usage examples
├── data/                  # Your projects
└── .env                   # Configuration
```

## Common Tasks

### Create a New Project

```python
from src.storage import ProjectManager

pm = ProjectManager()
pm.create_project("new_project", description="My new research")
```

### Add Documents to Existing Project

```python
from src.ingestion import DocumentPipeline
from src.storage import VectorStoreManager

pipeline = DocumentPipeline("my_project")
vector_store = VectorStoreManager("my_project")
index = vector_store.load_index()

# Ingest and add
docs = pipeline.ingest_file("new_paper.pdf")
vector_store.add_documents(index, docs)
```

### Query Without UI

```bash
python examples/simple_query.py
```

### Cross-Examine a Draft

```bash
python examples/cross_examine_example.py
```

---

## Troubleshooting

**"Tesseract not found"**
- Add Tesseract to PATH or set TESSERACT_CMD in .env

**"CUDA out of memory"**
- Reduce CHUNK_SIZE and TOP_K_RETRIEVAL in .env

**"No API key"**
- Set GOOGLE_API_KEY in .env or use Ollama

**Slow performance**
- Use smaller models (EMBEDDING_MODEL=BAAI/bge-small-en-v1.5)
- Or use Ollama locally

---

## Next Steps

1. Read [USAGE_GUIDE.md](USAGE_GUIDE.md) for detailed documentation
2. Check [InitialInstructions.md](InitialInstructions.md) for architecture
3. Explore [examples/](examples/) for code samples

## Support

- Issues: GitHub Issues
- Docs: README.md and USAGE_GUIDE.md
- Architecture: InitialInstructions.md
