"""
German-to-English translation using MarianMT models.

This module provides efficient translation of German academic texts
to English using the Helsinki-NLP MarianMT models from Hugging Face.
"""

from typing import List, Optional
from pathlib import Path

import torch
from transformers import MarianMTModel, MarianTokenizer, pipeline
from loguru import logger

from llama_index.core.schema import Document

from ..config import get_settings


class GermanTranslator:
    """
    German-to-English translator using MarianMT models.

    Uses the Helsinki-NLP/opus-mt-de-en model for high-quality
    translation of academic texts.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: int = 8
    ):
        """
        Initialize the translator.

        Args:
            model_name: HuggingFace model name (default from settings)
            device: Device to run on ('cuda', 'cpu', or None for auto)
            batch_size: Batch size for translation
        """
        settings = get_settings()
        self.model_name = model_name or settings.translation_model
        self.batch_size = batch_size

        # Auto-detect device
        if device is None:
            self.device = 0 if torch.cuda.is_available() else -1
        else:
            self.device = device

        logger.info(f"Initializing translator: {self.model_name}")

        # Load model and tokenizer
        self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
        self.model = MarianMTModel.from_pretrained(self.model_name)

        # Create translation pipeline
        self.translator = pipeline(
            "translation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=self.device,
            batch_size=self.batch_size
        )

        logger.success("Translator initialized successfully")

    def translate_text(self, text: str) -> str:
        """
        Translate German text to English.

        Args:
            text: German text to translate

        Returns:
            Translated English text
        """
        if not text.strip():
            return ""

        try:
            # Split into chunks if text is very long
            # MarianMT has a token limit
            max_length = 512
            chunks = self._split_into_chunks(text, max_length)

            # Translate chunks
            translated_chunks = []
            for chunk in chunks:
                result = self.translator(chunk, max_length=max_length)
                translated_chunks.append(result[0]['translation_text'])

            translated = " ".join(translated_chunks)

            logger.debug(
                f"Translated {len(text)} chars -> {len(translated)} chars"
            )

            return translated

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Return original text if translation fails
            return text

    def translate_document(
        self,
        text: str,
        source_path: Optional[Path] = None,
        **metadata
    ) -> Document:
        """
        Translate German text and create a LlamaIndex document.

        Args:
            text: German text to translate
            source_path: Path to source file (for metadata)
            **metadata: Additional metadata fields

        Returns:
            LlamaIndex Document with translated text
        """
        logger.info("Translating document to English")

        # Translate text
        translated_text = self.translate_text(text)

        # Build metadata
        doc_metadata = {
            "original_language": "de",
            "target_language": "en",
            "translation_model": self.model_name,
            "processing_method": "marian_mt",
            **metadata
        }

        if source_path:
            doc_metadata["source_file_path"] = str(Path(source_path).absolute())

        # Create document
        document = Document(
            text=translated_text,
            metadata=doc_metadata,
            id_=f"translated_{source_path.stem if source_path else 'text'}"
        )

        logger.success("Document translated successfully")
        return document

    def translate_file(self, file_path: Path | str) -> Document:
        """
        Load and translate a German text file.

        Args:
            file_path: Path to German text file

        Returns:
            LlamaIndex Document with translated text
        """
        file_path = Path(file_path)
        logger.info(f"Loading German file for translation: {file_path}")

        # Read file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                german_text = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                german_text = f.read()

        # Translate and create document
        return self.translate_document(
            text=german_text,
            source_path=file_path,
            document_type="translated_german_text"
        )

    def _split_into_chunks(self, text: str, max_tokens: int) -> List[str]:
        """
        Split text into chunks that fit within token limit.

        Tries to split at sentence boundaries when possible.

        Args:
            text: Text to split
            max_tokens: Maximum tokens per chunk

        Returns:
            List of text chunks
        """
        # Split by sentences first
        sentences = text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            # Rough estimate: ~1 token per 4 characters
            sentence_tokens = len(sentence) // 4

            if current_length + sentence_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_length += sentence_tokens

        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def batch_translate_files(self, file_paths: List[Path | str]) -> List[Document]:
        """
        Translate multiple files in batch.

        Args:
            file_paths: List of paths to German text files

        Returns:
            List of translated LlamaIndex Documents
        """
        logger.info(f"Batch translating {len(file_paths)} files")

        documents = []
        for i, path in enumerate(file_paths, 1):
            logger.info(f"Translating file {i}/{len(file_paths)}: {path}")
            doc = self.translate_file(path)
            documents.append(doc)

        logger.success(f"Batch translation complete: {len(documents)} documents")
        return documents

    def detect_language(self, text: str) -> str:
        """
        Simple language detection (German vs English).

        This is a basic heuristic - for production, use langdetect or similar.

        Args:
            text: Text to detect

        Returns:
            'de' for German, 'en' for English
        """
        # Count common German words/patterns
        german_indicators = ['der', 'die', 'das', 'und', 'ist', 'nicht', 'auch', 'für']
        english_indicators = ['the', 'and', 'is', 'not', 'also', 'for', 'with']

        text_lower = text.lower()

        german_count = sum(1 for word in german_indicators if f' {word} ' in text_lower)
        english_count = sum(1 for word in english_indicators if f' {word} ' in text_lower)

        return 'de' if german_count > english_count else 'en'

    def smart_translate(
        self,
        text: str,
        source_path: Optional[Path] = None,
        **metadata
    ) -> Document:
        """
        Automatically detect language and translate if needed.

        Args:
            text: Text to process
            source_path: Path to source file
            **metadata: Additional metadata

        Returns:
            LlamaIndex Document (translated if German, original if English)
        """
        detected_lang = self.detect_language(text)

        if detected_lang == 'de':
            logger.info("German text detected, translating...")
            return self.translate_document(text, source_path, **metadata)
        else:
            logger.info("English text detected, no translation needed")
            doc_metadata = {
                "original_language": "en",
                "processing_method": "no_translation",
                **metadata
            }
            if source_path:
                doc_metadata["source_file_path"] = str(Path(source_path).absolute())

            return Document(
                text=text,
                metadata=doc_metadata,
                id_=f"notranslate_{source_path.stem if source_path else 'text'}"
            )
