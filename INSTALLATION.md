# Installation Guide - Understanding Your Options

## What does `pip install -e .` do?

**Short answer:** Installs the package in "editable mode" from `pyproject.toml`

**Longer answer:**
- The `-e` flag means "editable" or "development mode"
- The `.` means "current directory"
- It reads `pyproject.toml` and installs all dependencies listed there
- **Advantage:** If you modify source code, changes are immediately available
- **Advantage:** One command installs everything
- **Disadvantage:** Installs ALL dependencies (~5GB)

## Alternative: requirements.txt

I've created **three options** for you:

### Option 1: Full Install (Original)
```bash
pip install -e .
```
**OR**
```bash
pip install -r requirements.txt
```
**Both do the same thing!**
- Installs all ~50 packages
- Size: ~5GB (mostly PyTorch for translation)
- Includes: OCR, translation, all integrations
- Best for: Your original use case (German texts, scanned PDFs)

### Option 2: Minimal Install (Lightweight)
```bash
pip install -r requirements-minimal.txt
```
- Installs only core RAG functionality
- Size: ~500MB-1GB
- Includes: Basic PDF search, chat interface
- **Missing:** OCR, translation, Obsidian, Zotero, paper finder
- Best for: Testing, English-only docs, clean PDFs

### Option 3: Custom Install (Pick Features)
```bash
pip install -r requirements-minimal.txt
pip install -r requirements-optional.txt
```
- Start minimal, add features you need
- Choose specific packages from requirements-optional.txt
- Best for: Customizing to your needs

---

## Which Should You Use?

### Use `pip install -r requirements.txt` if:
✅ You have German documents (needs translation = 2.5GB)
✅ You have scanned/poor quality PDFs (needs OCR)
✅ You use Obsidian Canvas files
✅ You want Zotero integration
✅ You want paper auto-download
✅ You want ALL features working

**This is YOU based on your requirements!**

### Use `pip install -r requirements-minimal.txt` if:
✅ You want to test the system first
✅ All your documents are English
✅ All your PDFs are clean (text-selectable)
✅ You don't need integrations yet
✅ You want to save disk space (~4GB savings)

**Start here to try it out, add features later**

---

## Installation Comparison

| Method | Command | Size | Features | Use When |
|--------|---------|------|----------|----------|
| **Editable** | `pip install -e .` | ~5GB | All | Development |
| **Full** | `pip install -r requirements.txt` | ~5GB | All | Production |
| **Minimal** | `pip install -r requirements-minimal.txt` | ~1GB | Core only | Testing |
| **Custom** | Install specific packages | Varies | Your choice | Selective |

---

## Step-by-Step Installation

### Recommended for Your Use Case

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Tesseract OCR (external)
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract tesseract-lang
# Linux: sudo apt-get install tesseract-ocr tesseract-ocr-deu

# 3. Configure
cp .env.example .env
# Edit .env and add GOOGLE_API_KEY

# 4. Test
python scripts/test_system.py

# 5. Use
python scripts/ingest_corpus.py
chainlit run src/ui/app.py
```

### Start Minimal, Add Later

```bash
# 1. Install core only
pip install -r requirements-minimal.txt

# 2. Test basic functionality
python scripts/test_system.py

# 3. Add features as needed:

# If you need OCR:
pip install opencv-python pytesseract pypdfium2 Pillow

# If you need translation:
pip install torch transformers sentencepiece

# If you need Zotero:
pip install pyzotero

# If you need paper download:
pip install paperscraper

# If you need web search:
pip install tavily-python langchain-community
```

---

## Understanding the Dependencies

### The Big Ones (Why It's 5GB)

**PyTorch: ~2GB**
- Needed for: German translation models
- Skip if: All documents are English
- Savings: ~2.5GB

**Transformers: ~500MB**
- Needed for: ML models, translation
- Skip if: No translation needed
- Savings: ~500MB

**OpenCV: ~100MB**
- Needed for: Image preprocessing for OCR
- Skip if: No scanned PDFs
- Savings: ~200MB (with related packages)

**Everything else: ~2GB**
- LlamaIndex, LangChain, ChromaDB, Chainlit, etc.
- **Required** - This is the core functionality

### What Can You Skip?

**You can safely skip:**
- `torch`, `transformers` (2.5GB) - if no German translation
- `opencv-python`, `pytesseract` (200MB) - if no scanned PDFs
- `pyjsoncanvas` (2MB) - if no Obsidian Canvas
- `pyzotero` (5MB) - if no Zotero integration
- `paperscraper` (10MB) - if no auto paper download
- `tavily-python` (5MB) - if no web search

**Total potential savings: ~3GB**

**But for your use case (German + scanned PDFs), you need most of it!**

---

## Why Not Just `pip install -e .`?

`pip install -e .` is great for:
✅ Development (code changes apply immediately)
✅ Contributing to the project
✅ One-command install

But `requirements.txt` is better for:
✅ Flexibility (choose what to install)
✅ Understanding what you're installing
✅ Saving disk space (minimal install)
✅ Standard Python practice
✅ Easier troubleshooting

**Both work! Use whichever you prefer.**

---

## Disk Space Summary

```
Full Install (requirements.txt):
├── PyTorch + Translation      2.5 GB  (skip if English-only)
├── OCR Libraries              0.2 GB  (skip if clean PDFs)
├── Core RAG Stack             2.0 GB  (required)
├── Integrations               0.3 GB  (optional)
└── Total                      5.0 GB

Minimal Install (requirements-minimal.txt):
├── Core RAG Stack             2.0 GB  (required)
└── Total                      2.0 GB
```

---

## My Recommendation

Based on your requirements (ADHD academic, Gestalt/Dewey, German texts, scanned PDFs):

### Use Full Install
```bash
pip install -r requirements.txt
```

**Why:**
1. You specifically mentioned German texts → need translation (2.5GB)
2. You mentioned "poor OCR readings" → need OCR pipeline (200MB)
3. Academic research → want all integrations
4. 5GB is reasonable for a comprehensive research tool

**The dependencies ARE necessary for your use case!**

### Alternative: Start Minimal
```bash
pip install -r requirements-minimal.txt
```
Test the system, then add features:
```bash
pip install torch transformers  # Add translation
pip install opencv-python pytesseract  # Add OCR
```

---

## Verifying Your Install

After installation, test what you have:

```bash
# Test system
python scripts/test_system.py

# Check specific features
python -c "import cv2; print('✓ OCR support available')"
python -c "import torch; print('✓ Translation support available')"
python -c "import pyzotero; print('✓ Zotero integration available')"
```

---

## Updating Dependencies

```bash
# Update all packages
pip install -r requirements.txt --upgrade

# Update specific package
pip install llama-index --upgrade
```

---

## Common Issues

### "Package not found"
**Solution:** Check package name, update pip
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### "Disk space full"
**Solution:** Use minimal install
```bash
pip install -r requirements-minimal.txt
```

### "Import error after install"
**Solution:** Reinstall problematic package
```bash
pip uninstall <package>
pip install <package>
```

---

## Summary

**Question:** Should I use `pip install -e .` or `requirements.txt`?

**Answer:** Either works!

- `pip install -e .` → Quick, installs everything, good for development
- `pip install -r requirements.txt` → Same result, more standard
- `pip install -r requirements-minimal.txt` → Lightweight, add features later

**For your use case:** Use `requirements.txt` (full install) because you need German translation and OCR support, which account for most of the size.

**Want to experiment?** Start with `requirements-minimal.txt` and add features as needed.

Both paths lead to a working system! 🚀
