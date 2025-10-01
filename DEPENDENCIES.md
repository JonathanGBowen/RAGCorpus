# Dependency Guide - What Do You Really Need?

## TL;DR - Installation Options

### Option 1: Full Install (Recommended)
**Everything works, all features available**
```bash
pip install -r requirements.txt
```
**Size:** ~4-5GB (mostly PyTorch for translation)

### Option 2: Minimal Install
**Basic functionality only**
```bash
pip install -r requirements-minimal.txt
```
**Size:** ~500MB-1GB
**Missing:** OCR, translation, Obsidian, Zotero, paper finder, BM25, web search

### Option 3: Custom Install
**Pick what you need**
```bash
pip install -r requirements-minimal.txt
pip install -r requirements-optional.txt  # or install specific packages
```

---

## 📊 Dependency Breakdown

### Core Framework (~500MB)
**Required for basic operation**

| Package | Size | Why Needed | Can Skip? |
|---------|------|-----------|-----------|
| llama-index | ~100MB | Document processing, indexing | ❌ No |
| chromadb | ~50MB | Vector storage | ❌ No |
| chainlit | ~100MB | User interface | ❌ No |
| langchain/langgraph | ~200MB | Agent framework | ❌ No |
| pydantic, loguru, etc. | ~50MB | Core utilities | ❌ No |

**Total Core:** ~500MB

### OCR Pipeline (~200MB)
**For scanned PDFs with poor quality**

| Package | Size | Why Needed | Can Skip? |
|---------|------|-----------|-----------|
| opencv-python | ~100MB | Image preprocessing | ✅ If no scanned PDFs |
| pytesseract | ~5MB | OCR engine interface | ✅ If no scanned PDFs |
| pypdfium2 | ~50MB | PDF rendering | ✅ If no scanned PDFs |
| Pillow | ~20MB | Image handling | ✅ If no scanned PDFs |

**Can skip if:** You only have clean, text-based PDFs

### Translation Pipeline (~2-3GB!)
**For German academic texts**

| Package | Size | Why Needed | Can Skip? |
|---------|------|-----------|-----------|
| torch | ~2GB | Neural network backend | ✅ If no German texts |
| transformers | ~500MB | ML models | ✅ If no German texts |
| sentencepiece | ~10MB | Tokenization | ✅ If no German texts |

**Can skip if:** All your documents are in English

**⚠️ This is the biggest dependency!** If you don't need German translation, you save 2.5GB+

### Integrations (~50MB)
**External services**

| Package | Size | Why Needed | Can Skip? |
|---------|------|-----------|-----------|
| pyzotero | ~5MB | Zotero integration | ✅ If not using Zotero |
| paperscraper | ~10MB | Paper download | ✅ If not auto-downloading |
| tavily-python | ~5MB | Web search | ✅ If no web search needed |
| pyjsoncanvas | ~2MB | Obsidian Canvas | ✅ If not using Canvas |

**Can skip if:** You don't use these specific features

### LLM Options
**Choose one**

| Option | Size | Pros | Cons |
|--------|------|------|------|
| Gemini (API) | ~20MB | Fast, powerful, cheap | Needs internet, API key |
| Ollama (local) | ~20MB | Privacy, free, offline | Need to download models separately |

---

## 🎯 Recommended Configurations

### 1. Academic Researcher (Full Featured)
**Use case:** Gestalt/Dewey research, German texts, scanned books
```bash
pip install -r requirements.txt
```
**Includes:** Everything
**Size:** ~5GB
**Best for:** Your original use case

### 2. English-Only, Clean PDFs
**Use case:** Modern papers, no scanned docs, no German
```bash
pip install -r requirements-minimal.txt
# Optionally add:
pip install llama-index-retrievers-bm25  # Better search
pip install tavily-python  # Web search
```
**Size:** ~1GB
**Missing:** OCR, translation, Obsidian

### 3. Local-Only (No External APIs)
**Use case:** Privacy-focused, offline work
```bash
pip install -r requirements-minimal.txt
pip install llama-index-llms-ollama
# Then install Ollama separately
```
**Size:** ~1GB (+ Ollama models)
**Best for:** Offline research, privacy

### 4. Minimal Cloud Research
**Use case:** Simple semantic search, Gemini API
```bash
pip install -r requirements-minimal.txt
```
**Size:** ~500MB
**Best for:** Getting started quickly

---

## 💾 Storage Impact

### Disk Space Breakdown
```
Core packages:           ~500MB
OCR support:            ~200MB
Translation (PyTorch):  ~2.5GB  ⬅ BIGGEST!
Integrations:           ~50MB
Your documents:         varies
Vector embeddings:      ~500MB per 1000 docs
Models (downloaded):    ~1GB per embedding model
-----------------------------------
Total (full install):   ~4-5GB
```

### Runtime Memory
- Minimal: ~2GB RAM
- With translation: ~4GB RAM
- With large corpus: ~6GB RAM
- GPU optional: Speeds up embeddings

---

## ❓ Decision Guide

### Do I need OCR support?
**YES if:**
- You have scanned books/papers
- PDFs are image-based
- OCR quality is poor

**NO if:**
- All PDFs are clean/modern
- Text is selectable in PDFs

### Do I need translation?
**YES if:**
- You have German academic texts
- Your corpus is multilingual

**NO if:**
- All documents are in English
- You can translate separately

**⚠️ Translation = 2.5GB! Skip this to save space**

### Do I need Zotero integration?
**YES if:**
- You use Zotero for references
- You want citation management

**NO if:**
- You don't use Zotero
- You manage references elsewhere

### Do I need paper auto-download?
**YES if:**
- You frequently need papers by DOI
- You want auto-ingestion

**NO if:**
- You manually download papers
- You don't use DOIs

---

## 🚀 Quick Start Recommendations

### For Your Original Use Case
**Gestalt psychology + Dewey + German texts + scanned books**
```bash
pip install -r requirements.txt
```
**You need everything!** Your requirements justify the full install.

### If You Want to Start Light
```bash
# Start minimal
pip install -r requirements-minimal.txt

# Add OCR later if needed
pip install opencv-python pytesseract pypdfium2 Pillow

# Add translation later if needed
pip install torch transformers sentencepiece
```

---

## 🔍 Verifying Your Install

### Check what you have:
```bash
pip list | grep -E "(llama-index|langchain|chromadb|torch)"
```

### Test specific features:
```bash
# Test basic system
python scripts/test_system.py

# Test OCR (if installed)
python -c "import cv2; print('OCR: OK')"

# Test translation (if installed)
python -c "import torch; print('Translation: OK')"
```

---

## 📦 Package Purpose Reference

### Why each package exists:

**llama-index-*** - Document processing pipeline
- Core framework for RAG
- Handles chunking, indexing, retrieval

**langchain/langgraph** - Agent framework
- ReAct reasoning
- Tool orchestration
- Memory management

**chromadb** - Vector database
- Stores embeddings
- Fast similarity search
- Local-first

**torch** - Neural networks
- Required for translation models
- Required for custom embedding models
- **HUGE** (~2GB) but needed for ML

**opencv-python** - Image processing
- Preprocessing for OCR
- Deskewing, denoising, binarization

**transformers** - ML models
- Translation models
- Can load embedding models
- Hugging Face ecosystem

**chainlit** - User interface
- Chat application
- File uploads
- Visual feedback

---

## ✅ My Recommendation

For your **ADHD academic use case with Dewey/Gestalt/German texts**:

### Use full requirements.txt
**Why:**
1. You mentioned German texts → need translation
2. You mentioned "poor OCR readings" → need OCR pipeline
3. Academic research → want all integrations
4. 5GB disk space is reasonable for a research tool

### But you could skip:
- `paperscraper` if you don't auto-download papers
- `tavily-python` if you don't need web search
- `pyzotero` if you don't use Zotero

That would save ~50MB (trivial compared to PyTorch)

---

## 🎯 Bottom Line

**The dependencies are heavy BUT justified:**
- PyTorch (2GB) - Needed for German translation
- OpenCV (100MB) - Needed for scanned PDFs
- LlamaIndex/LangChain (300MB) - Core RAG functionality
- Everything else (2GB) - Supporting libraries

**Your use case needs most of this!** The full install is appropriate.

**Want to save space?** Skip translation (saves 2.5GB) if all docs are English.

---

## 📝 Installation Commands

### Full Install (Recommended for you)
```bash
pip install -r requirements.txt
```

### Minimal Install
```bash
pip install -r requirements-minimal.txt
```

### Custom Install
```bash
# Core
pip install -r requirements-minimal.txt

# Add what you need
pip install opencv-python pytesseract pypdfium2  # OCR
pip install torch transformers  # Translation
pip install pyzotero  # Zotero
```

---

**Summary:** Yes, you need most of these dependencies for your use case. The full install is ~5GB but includes everything you asked for (OCR, translation, integrations). If you want to start lighter, use requirements-minimal.txt and add features as needed.
