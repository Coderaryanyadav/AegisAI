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
    def validate_safe_path(target_path: str) -> str:
        """Resolves target_path and verifies it resides strictly within the user's Aegis AI directory or temp folder."""
        from aegis_backend.database import AEGIS_DIR
        import tempfile
        
        resolved_target = os.path.abspath(target_path)
        resolved_aegis = os.path.abspath(AEGIS_DIR)
        resolved_temp = os.path.abspath(tempfile.gettempdir())
        
        if not (resolved_target.startswith(resolved_aegis) or resolved_target.startswith(resolved_temp)):
            raise PermissionError("Access Denied: Path traversal attempt detected outside sandbox boundaries.")
        return resolved_target

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
        safe_path = cls.validate_safe_path(file_path)
        if not os.path.exists(safe_path):
            raise FileNotFoundError(f"File not found: {safe_path}")

        logger.info(f"Processing document: {file_path}")
        doc = None
        try:
            try:
                doc = fitz.open(safe_path)
            except Exception as e:
                logger.error(f"Error opening PDF via PyMuPDF: {e}")
                raise ValueError(f"Failed to parse PDF document: {e}")

            text_content = [page.get_text() for page in doc]
            full_text = "\n".join(text_content).strip()
            
            # If we got enough text, return it directly
            if len(full_text) >= min_char_threshold:
                logger.info("Successfully extracted digital text from PDF.")
                return full_text

            # Otherwise, fall back to OCR
            logger.warning("Extracted text is empty or too short. Attempting OCR fallback...")
            
            if not cls.is_tesseract_available():
                logger.warning("OCR is required for this scanned document, but Tesseract is not installed. Falling back to empty text.")
                return ""

            ocr_text_content = ["" for _ in range(len(doc))]
            import concurrent.futures
            
            def process_page(page_idx):
                logger.info(f"Running OCR on page {page_idx + 1}/{len(doc)}...")
                page = doc[page_idx]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(image_data))
                return pytesseract.image_to_string(image)
                
            # Restrict concurrency to avoid CPU starvation on multi-page OCR processes
            max_workers = max(1, min(4, (os.cpu_count() or 2) // 2))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_page, i): i for i in range(len(doc))}
                for future in concurrent.futures.as_completed(futures):
                    page_idx = futures[future]
                    try:
                        ocr_text_content[page_idx] = future.result()
                    except Exception as e:
                        logger.error(f"OCR failed for page {page_idx + 1}: {e}")
                        raise

            full_ocr_text = "\n".join(ocr_text_content).strip()
            logger.info("Successfully extracted text using OCR.")
            return full_ocr_text
        finally:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass

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
