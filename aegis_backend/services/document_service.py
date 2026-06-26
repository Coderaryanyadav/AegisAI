import os
import asyncio
import logging
from typing import List
from aegis_backend.database import AsyncSessionLocal, Document
from aegis_backend.vector_store import vector_store
from aegis_backend.document_processor import DocumentProcessor

logger = logging.getLogger("aegis_ai.backend")

class DocumentService:
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 400, chunk_overlap: int = 80) -> List[str]:
        """Helper to split document text into dense context chunks."""
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            i += chunk_size - chunk_overlap
            if i >= len(words):
                break
        return chunks

    @staticmethod
    def decrypt_and_extract(file_path: str, original_name: str) -> str:
        """Synchronous CPU-bound parsing function run in a separate thread."""
        from aegis_backend.database import cipher
        import tempfile
        
        # Decrypt binary file
        with open(file_path, "rb") as enc_file:
            encrypted_data = enc_file.read()
        raw_data = cipher.decrypt(encrypted_data)

        if original_name.lower().endswith(".txt"):
            text = raw_data.decode("utf-8", errors="ignore")
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(raw_data)
                tmp_path = tmp.name

            try:
                # Extract text using PyMuPDF or Tesseract fallback
                text = DocumentProcessor.extract_text(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        # Save raw content in local file system encrypted
        raw_text_path = file_path + ".txt"
        encrypted_text = cipher.encrypt(text.encode('utf-8'))
        with open(raw_text_path, "wb") as f:
            f.write(encrypted_text)
            
        return text

    @staticmethod
    async def process_uploaded_document_task(doc_id: int, file_path: str):
        """Background task to extract and vector-index documents asynchronously."""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            stmt = select(Document).filter(Document.id == doc_id)
            res = await db.execute(stmt)
            doc = res.scalars().first()
            if not doc:
                return

            doc.status = "processing"
            await db.commit()

            try:
                # Offload heavy decryption & extraction to thread pool to avoid blocking event loop
                text = await asyncio.to_thread(DocumentService.decrypt_and_extract, file_path, doc.original_name)
                
                # Chunk text
                chunks = DocumentService.chunk_text(text)
                vector_chunks = []
                for i, chunk in enumerate(chunks):
                    vector_chunks.append({
                        "id": f"doc_{doc.id}_chunk_{i}",
                        "content": chunk,
                        "metadata": {
                            "document_id": doc.id,
                            "matter_id": doc.matter_id or 0,
                            "filename": doc.original_name
                        }
                    })

                # Add to ChromaDB vector store
                if vector_chunks:
                    vector_store.add_chunks(vector_chunks)

                doc.status = "processed"
                await db.commit()
                logger.info(f"Processed and indexed document: {doc.original_name}")
            except Exception as e:
                logger.error(f"Failed to process document {doc_id}: {e}")
                await db.rollback()
                try:
                    doc.status = "failed"
                    await db.commit()
                except Exception as commit_err:
                    logger.error(f"Failed to commit failed status for document {doc_id}: {commit_err}")
                    await db.rollback()
