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
    def chunk_text(text: str, chunk_size: int = 400, chunk_overlap: int = 80, document_name: str = "") -> List[str]:
        """Helper to split document text into dense context chunks using legal structure awareness."""
        from aegis_backend.core.legal_chunker import LegalChunker
        return LegalChunker.split_legal_text(text, document_name, chunk_size, chunk_overlap)

    @staticmethod
    def process_document_sync(dest_path: str, original_name: str, tmp_path: str = None) -> str:
        """Synchronous CPU-bound parsing function run in a separate thread.
        If tmp_path is provided (new upload), it encrypts the plaintext tmp_path into dest_path.
        Otherwise (reprocessing), it decrypts dest_path.
        """
        from aegis_backend.database import cipher
        import tempfile
        
        if tmp_path and os.path.exists(tmp_path):
            # Encrypt plaintext to vault
            with open(tmp_path, "rb") as f_in:
                raw_data = f_in.read()
            encrypted_data = cipher.encrypt(raw_data)
            with open(dest_path, "wb") as f_out:
                f_out.write(encrypted_data)
        else:
            # Decrypt existing vault file
            with open(dest_path, "rb") as enc_file:
                encrypted_data = enc_file.read()
            raw_data = cipher.decrypt(encrypted_data)
            tmp_path = None

        if original_name.lower().endswith(".txt"):
            text = raw_data.decode("utf-8", errors="ignore")
        else:
            working_path = tmp_path
            created_tmp = False
            if not working_path:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(raw_data)
                    working_path = tmp.name
                    created_tmp = True

            try:
                # Extract text using PyMuPDF or Tesseract fallback
                text = DocumentProcessor.extract_text(working_path)
            finally:
                if created_tmp and os.path.exists(working_path):
                    os.remove(working_path)
                elif tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        # Save raw content in local file system encrypted
        raw_text_path = dest_path + ".txt"
        encrypted_text = cipher.encrypt(text.encode('utf-8'))
        with open(raw_text_path, "wb") as f:
            f.write(encrypted_text)
            
        return text

    @staticmethod
    async def process_uploaded_document_task(doc_id: int, file_path: str, tmp_path: str = None):
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
                # Offload heavy encryption & extraction to thread pool to avoid blocking event loop
                text = await asyncio.to_thread(DocumentService.process_document_sync, file_path, doc.original_name, tmp_path)
                
                # Chunk text
                chunks = DocumentService.chunk_text(text, document_name=doc.original_name)
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

    @staticmethod
    async def get_documents_list(
        db: AsyncSession,
        current_user: User,
        matter_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Document], int]:
        from aegis_backend.repositories.document_repository import DocumentRepository
        repo = DocumentRepository(db)
        if current_user.role == "client":
            return await repo.list_documents_for_client(
                client_email=current_user.email,
                matter_id=matter_id,
                skip=skip,
                limit=limit
            )
        return await repo.list_documents(
            matter_id=matter_id,
            skip=skip,
            limit=limit
        )

    @staticmethod
    async def create_document_record(
        db: AsyncSession,
        matter_id: Optional[int],
        original_name: str,
        stored_uuid: str,
        file_path: str,
        file_hash: str
    ) -> Document:
        from aegis_backend.repositories.document_repository import DocumentRepository
        repo = DocumentRepository(db)
        
        # Check duplicate
        existing = await repo.get_by_hash(file_hash)
        if existing:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate document already uploaded (ID: {existing.id}, Name: {existing.original_name})"
            )

        doc = Document(
            matter_id=matter_id,
            original_name=original_name,
            stored_uuid=stored_uuid,
            file_path=file_path,
            file_hash=file_hash,
            status="uploaded"
        )
        return await repo.create(doc)

    @staticmethod
    async def remove_document(db: AsyncSession, doc_id: int, current_user: User):
        from aegis_backend.repositories.document_repository import DocumentRepository
        from aegis_backend.core.security import check_document_access
        from aegis_backend.database import Matter
        from sqlalchemy import select
        from fastapi import HTTPException
        
        repo = DocumentRepository(db)
        doc = await check_document_access(db, current_user, doc_id)
        
        if current_user.role == "lawyer" and doc.matter_id:
            stmt = select(Matter).filter(Matter.id == doc.matter_id)
            res = await db.execute(stmt)
            matter = res.scalars().first()
            if not matter:
                raise HTTPException(status_code=403, detail="Matter not found for this document")

        # Delete vectors
        try:
            vector_store.delete_document_vectors(doc.id)
        except Exception as e:
            logger.warning(f"Error removing vectors for doc {doc_id}: {e}")

        # Delete physical files
        filename = os.path.basename(doc.file_path)
        real_path = os.path.join(AEGIS_DIR, "vault", filename)
        txt_path = real_path + ".txt"
        if os.path.exists(real_path):
            os.remove(real_path)
        if os.path.exists(txt_path):
            os.remove(txt_path)

        await repo.delete(doc)

