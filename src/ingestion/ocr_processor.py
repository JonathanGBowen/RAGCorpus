"""
OCR preprocessing pipeline using OpenCV and Tesseract.

This module implements a robust OCR pipeline with advanced image preprocessing
to handle poorly scanned PDFs and documents with atrocious OCR quality.
"""

import cv2
import numpy as np
import pytesseract
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

import pypdfium2 as pdfium
from PIL import Image
from loguru import logger

from llama_index.core.schema import Document

from ..config import get_settings


@dataclass
class OCRResult:
    """Result of OCR processing for a single page."""

    page_number: int
    text: str
    confidence: float
    preprocessed_successfully: bool


class OCRProcessor:
    """
    Advanced OCR processor with OpenCV preprocessing pipeline.

    This class implements the full preprocessing workflow:
    1. Rescaling to optimal DPI (300)
    2. Grayscale conversion
    3. Adaptive binarization for uneven lighting
    4. Deskewing to correct rotation
    5. Noise removal
    6. Tesseract OCR with German language support
    """

    def __init__(self, languages: Optional[str] = None, target_dpi: int = 300):
        """
        Initialize OCR processor.

        Args:
            languages: Tesseract language codes (e.g., 'eng+deu')
            target_dpi: Target DPI for rescaling (default: 300)
        """
        settings = get_settings()
        self.languages = languages or settings.ocr_languages
        self.target_dpi = target_dpi

        # Set Tesseract command path if specified
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

        logger.info(f"Initialized OCR processor with languages: {self.languages}")

    def process_pdf(self, pdf_path: Path | str) -> Document:
        """
        Process a scanned PDF with OCR.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            LlamaIndex Document with extracted text and metadata
        """
        pdf_path = Path(pdf_path)
        logger.info(f"Processing PDF with OCR: {pdf_path}")

        # Extract pages as images
        pages = self._extract_pdf_pages(pdf_path)

        # Process each page
        ocr_results: List[OCRResult] = []
        for page_num, page_image in enumerate(pages, start=1):
            result = self._process_page(page_image, page_num)
            ocr_results.append(result)

        # Combine text from all pages
        full_text = "\n\n".join(
            f"--- Page {r.page_number} ---\n{r.text}"
            for r in ocr_results if r.text.strip()
        )

        # Calculate average confidence
        avg_confidence = np.mean([r.confidence for r in ocr_results])

        # Create LlamaIndex document
        metadata = {
            "source_file_path": str(pdf_path.absolute()),
            "document_type": "scanned_pdf",
            "total_pages": len(pages),
            "ocr_confidence": float(avg_confidence),
            "ocr_language": self.languages,
            "processing_method": "opencv_tesseract"
        }

        document = Document(
            text=full_text,
            metadata=metadata,
            id_=f"ocr_{pdf_path.stem}"
        )

        logger.success(
            f"OCR complete: {len(pages)} pages, "
            f"avg confidence: {avg_confidence:.2%}"
        )

        return document

    def _extract_pdf_pages(self, pdf_path: Path) -> List[np.ndarray]:
        """
        Extract pages from PDF as images.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of page images as numpy arrays
        """
        pages = []

        try:
            pdf = pdfium.PdfDocument(str(pdf_path))

            for page_num in range(len(pdf)):
                page = pdf[page_num]

                # Render at target DPI
                pil_image = page.render(
                    scale=self.target_dpi / 72.0
                ).to_pil()

                # Convert to numpy array for OpenCV
                img_array = np.array(pil_image)

                # Convert RGB to BGR for OpenCV
                if len(img_array.shape) == 3:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                pages.append(img_array)

            logger.debug(f"Extracted {len(pages)} pages from PDF")
            return pages

        except Exception as e:
            logger.error(f"Failed to extract PDF pages: {e}")
            raise

    def _process_page(self, image: np.ndarray, page_num: int) -> OCRResult:
        """
        Apply OpenCV preprocessing pipeline and run Tesseract OCR.

        Args:
            image: Input image as numpy array
            page_num: Page number for logging

        Returns:
            OCRResult with extracted text and metadata
        """
        try:
            # Step 1: Grayscale conversion
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # Step 2: Adaptive thresholding for binarization
            # Handles uneven lighting better than global threshold
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=11,
                C=2
            )

            # Step 3: Deskewing
            deskewed = self._deskew_image(binary)

            # Step 4: Noise removal
            denoised = cv2.fastNlMeansDenoising(deskewed, h=10)

            # Step 5: Morphological operations to clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
            cleaned = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)

            # Run Tesseract OCR
            text = pytesseract.image_to_string(
                cleaned,
                lang=self.languages,
                config='--psm 1'  # Automatic page segmentation with OSD
            )

            # Get confidence scores
            data = pytesseract.image_to_data(
                cleaned,
                lang=self.languages,
                output_type=pytesseract.Output.DICT
            )
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = np.mean(confidences) / 100.0 if confidences else 0.0

            logger.debug(
                f"Page {page_num}: {len(text)} chars, "
                f"confidence: {avg_confidence:.2%}"
            )

            return OCRResult(
                page_number=page_num,
                text=text,
                confidence=avg_confidence,
                preprocessed_successfully=True
            )

        except Exception as e:
            logger.warning(f"OCR failed for page {page_num}: {e}")
            return OCRResult(
                page_number=page_num,
                text="",
                confidence=0.0,
                preprocessed_successfully=False
            )

    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """
        Detect and correct page skew.

        Args:
            image: Binary image

        Returns:
            Deskewed image
        """
        # Find coordinates of all non-zero points
        coords = np.column_stack(np.where(image > 0))

        # Find minimum area rectangle
        angle = cv2.minAreaRect(coords)[-1]

        # Correct angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Rotate image if angle is significant
        if abs(angle) > 0.5:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image,
                M,
                (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            return rotated

        return image

    def enhance_with_llm(
        self,
        text: str,
        llm_client: Optional[object] = None
    ) -> str:
        """
        Use an LLM to clean up and enhance OCR output.

        This method can fix common OCR errors like character substitutions,
        missing spaces, and formatting issues.

        Args:
            text: Raw OCR text
            llm_client: LLM client (Gemini or Ollama)

        Returns:
            Enhanced text
        """
        if not llm_client or not text.strip():
            return text

        prompt = f"""You are an expert at cleaning up OCR-generated text.
The following text was extracted from a scanned academic document using OCR.
Please fix obvious OCR errors such as:
- Character substitutions (e.g., 'rn' -> 'm', '1' -> 'l', '0' -> 'O')
- Missing or extra spaces
- Broken words across lines
- Formatting issues

Preserve the original meaning and structure. Do not add new content or interpretations.

OCR Text:
{text}

Cleaned Text:"""

        try:
            # This would use the configured LLM (Gemini or Ollama)
            # Implementation depends on llm_client interface
            enhanced = llm_client.complete(prompt).text
            logger.debug("Enhanced OCR text with LLM")
            return enhanced
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            return text
