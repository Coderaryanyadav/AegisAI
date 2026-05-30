import os
import pypdf
import pdfplumber
import hashlib
from typing import Dict, Any, Optional
from legal_ai.auth.security import decrypt_data, encrypt_data
from legal_ai.config import ENCRYPTED_FILES_DIR

class DocumentIngestor:
    @staticmethod
    def calculate_file_hash(data: bytes) -> str:
        """Calculate SHA-256 hash of file content to detect duplicates."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def encrypt_and_store_file(data: bytes, filename: str) -> str:
        """Encrypt file data and store it securely on the filesystem."""
        encrypted_data = encrypt_data(data)
        file_path = os.path.join(ENCRYPTED_FILES_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(encrypted_data)
        return file_path

    @staticmethod
    def read_encrypted_file(file_path: str) -> bytes:
        """Read and decrypt file data from storage."""
        with open(file_path, "rb") as f:
            encrypted_data = f.read()
        return decrypt_data(encrypted_data)

    def extract_text(self, file_path: str, original_filename: str) -> str:
        """Decrypt file and extract clean text from it depending on file extension."""
        decrypted_bytes = self.read_encrypted_file(file_path)
        ext = os.path.splitext(original_filename.lower())[1]

        if ext == ".txt":
            return decrypted_bytes.decode("utf-8", errors="ignore")
        elif ext == ".pdf":
            return self._extract_text_from_pdf_bytes(decrypted_bytes)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using pdfplumber, falling back to pypdf."""
        import io
        text_content = []
        
        # Try pdfplumber first (higher quality text layout preservation)
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text()
                    if page_text:
                        # Append marker for page tracking in citations
                        text_content.append(f"\n--- PAGE {page_num} ---\n{page_text}")
            
            extracted_text = "".join(text_content).strip()
            if len(extracted_text) > 100:
                return extracted_text
        except Exception as e:
            print(f"[*] pdfplumber extraction failed: {e}. Falling back to pypdf.")

        # Fallback to pypdf
        text_content = []
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(f"\n--- PAGE {page_num} ---\n{page_text}")
            
            extracted_text = "".join(text_content).strip()
            if len(extracted_text) > 0:
                return extracted_text
        except Exception as e:
            print(f"[!] pypdf extraction failed: {e}")

        # OCR Fallback Notice (if text length is still empty, the document is likely scanned)
        # In a real local server, pytesseract or ocrmypdf would be called here.
        # We raise a friendly exception to indicate OCR requirement.
        raise ValueError(
            "No readable text found in PDF. The document may be a scanned image or image-only PDF. "
            "Please upload a searchable PDF or run OCR locally first."
        )
