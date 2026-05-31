import os
import fitz  # PyMuPDF
from PIL import Image
import io
import logging

logger = logging.getLogger("aegis_ai.document_processor")

try:
    import pytesseract
except ImportError:
    pytesseract = None

class DocumentProcessor:
    """Processes legal PDFs, extracting digital text or falling back to OCR if scanned."""

    @staticmethod
    def is_tesseract_available() -> bool:
        if pytesseract is None:
            return False
        try:
            # Quick check if tesseract binary is runnable
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @classmethod
    def extract_text(cls, file_path: str, min_char_threshold: int = 150) -> str:
        """
        Extracts text from a PDF file.
        If extracted text length is below min_char_threshold, falls back to OCR.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Processing document: {file_path}")
        text_content = []
        doc = None

        try:
            doc = fitz.open(file_path)
            for page in doc:
                text_content.append(page.get_text())
        except Exception as e:
            logger.error(f"Error opening or reading PDF via PyMuPDF: {e}")
            if doc:
                doc.close()
            raise ValueError(f"Failed to parse PDF document: {e}")

        full_text = "\n".join(text_content).strip()
        
        # If we got enough text, return it directly
        if len(full_text) >= min_char_threshold:
            logger.info("Successfully extracted digital text from PDF.")
            doc.close()
            return full_text

        # Otherwise, fall back to OCR
        logger.warning("Extracted text is empty or too short. Attempting OCR fallback...")
        
        if not cls.is_tesseract_available():
            doc.close()
            raise RuntimeError(
                "OCR is required for this scanned document, but Tesseract is not installed "
                "or not found in the system PATH. Please install Tesseract (e.g., 'brew install tesseract' on macOS)."
            )

        ocr_text_content = []
        try:
            for page_idx, page in enumerate(doc):
                logger.info(f"Running OCR on page {page_idx + 1}/{len(doc)}...")
                # Render page to a high-resolution image (300 DPI is standard for OCR)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(image_data))
                
                # Perform OCR on the image
                page_text = pytesseract.image_to_string(image)
                ocr_text_content.append(page_text)
            
            full_ocr_text = "\n".join(ocr_text_content).strip()
            logger.info("Successfully extracted text using OCR.")
            return full_ocr_text
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise RuntimeError(f"OCR processing failed: {e}")
        finally:
            if doc:
                doc.close()

if __name__ == "__main__":
    # Quick CLI test
    import sys
    if len(sys.argv) > 1:
        test_pdf = sys.argv[1]
        try:
            print("Extracted Text:")
            print(DocumentProcessor.extract_text(test_pdf))
        except Exception as ex:
            print(f"Error: {ex}")
    else:
        print("Please provide a path to a PDF file to test.")
