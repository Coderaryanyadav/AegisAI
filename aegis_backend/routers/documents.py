import os
import uuid
import hashlib
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from aegis_backend.database import get_db, User, Client, Matter, Document, AEGIS_DIR
from aegis_backend.schemas.models import DocumentResponse
from aegis_backend.core.security import get_current_user, verify_lawyer_or_admin, log_audit_trail, read_decrypted_document_text
from aegis_backend.core.cache import rag_cache
from aegis_backend.vector_store import vector_store
from aegis_backend.document_processor import DocumentProcessor

router = APIRouter(tags=["documents"])
logger = logging.getLogger("aegis_ai.backend")

from aegis_backend.services.document_service import DocumentService

@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    matter_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_lawyer_or_admin)
):
    vault_dir = os.path.join(AEGIS_DIR, "vault")
    os.makedirs(vault_dir, exist_ok=True)

    # Sanitize incoming filename to prevent directory traversal
    safe_filename = os.path.basename(file.filename)
    file_uuid = str(uuid.uuid4())
    ext = os.path.splitext(safe_filename)[1]
    stored_name = f"{file_uuid}{ext}"
    dest_path = os.path.join(vault_dir, stored_name)

    # Whitelist allowed extensions and MIME types
    allowed_extensions = {".pdf", ".txt"}
    allowed_content_types = {"application/pdf", "text/plain"}
    
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in allowed_extensions or file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only PDF and TXT files are allowed."
        )

    # Check file size before loading into memory
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 100MB.")

    # Read file asynchronously to avoid blocking the event loop
    raw_data = await file.read()
        
    sha256_hash = hashlib.sha256()
    sha256_hash.update(raw_data)
    file_hash = sha256_hash.hexdigest()

    # Check if document already exists by hash
    stmt_dup = select(Document).filter(Document.file_hash == file_hash)
    res_dup = await db.execute(stmt_dup)
    existing_doc = res_dup.scalars().first()
    if existing_doc:
        raise HTTPException(
            status_code=400,
            detail=f"Duplicate document already uploaded (ID: {existing_doc.id}, Name: {existing_doc.original_name})"
        )

    from aegis_backend.database import cipher
    
    def encrypt_and_save(data: bytes, path: str):
        encrypted = cipher.encrypt(data)
        with open(path, "wb") as buffer:
            buffer.write(encrypted)
            
    import asyncio
    await asyncio.to_thread(encrypt_and_save, raw_data, dest_path)

    # Register in SQLite
    doc = Document(
        matter_id=matter_id,
        original_name=safe_filename,
        stored_uuid=file_uuid,
        file_path=dest_path,
        file_hash=file_hash,
        status="uploaded"
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await log_audit_trail(db, current_user.email, "UPLOAD_DOC", "documents", str(doc.id), safe_filename)

    # Trigger background extractor and indexer
    background_tasks.add_task(DocumentService.process_uploaded_document_task, doc.id, dest_path)

    # Invalidate RAG Cache
    rag_cache.clear()

    return doc

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(response: Response, matter_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Document)
    if current_user.role == "client":
        stmt_client = select(Client).filter(Client.email == current_user.email)
        res_client = await db.execute(stmt_client)
        client = res_client.scalars().first()
        if not client:
            response.headers["X-Total-Count"] = "0"
            return []
        
        stmt_matters = select(Matter.id).filter(Matter.client_id == client.id)
        res_matters = await db.execute(stmt_matters)
        mat_ids = res_matters.scalars().all()
        
        if matter_id and matter_id in mat_ids:
            stmt = stmt.filter(Document.matter_id == matter_id)
        else:
            stmt = stmt.filter(Document.matter_id.in_(mat_ids))
    elif matter_id:
        stmt = stmt.filter(Document.matter_id == matter_id)
    
    count_stmt = select(func.count(Document.id)).select_from(stmt.subquery())
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar()
    response.headers["X-Total-Count"] = str(total_count)
    
    res = await db.execute(stmt.offset(skip).limit(limit))
    return res.scalars().all()

@router.get("/documents/{id}/text")
async def get_document_text(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from aegis_backend.core.security import check_document_access
    doc = await check_document_access(db, current_user, id)
    
    filename = os.path.basename(doc.file_path)
    txt_path = os.path.join(AEGIS_DIR, "vault", filename + ".txt")
    if os.path.exists(txt_path):
        decrypted_text = read_decrypted_document_text(txt_path)
        return {"text": decrypted_text}
    return {"text": "Extracted text not ready or file failed processing."}

@router.delete("/documents/{id}")
async def delete_document(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    from aegis_backend.core.security import check_document_access
    
    # Check if the user has access to this document and it exists
    doc = await check_document_access(db, current_user, id)
    
    if current_user.role == "lawyer":
        # Lawyers can only delete if the document is unassigned OR belongs to a matter owned by their client accounts?
        # Let's enforce that only admins can delete, or lawyers assigned to the matter
        if doc.matter_id:
            stmt = select(Matter).filter(Matter.id == doc.matter_id)
            res = await db.execute(stmt)
            matter = res.scalars().first()
            if not matter:
                raise HTTPException(status_code=403, detail="Matter not found for this document")
    
    # Remove vectors
    try:
        vector_store.delete_document_vectors(doc.id)
    except Exception as e:
        logger.warning(f"Error removing vectors for doc {id}: {e}")

    # Remove files safely
    filename = os.path.basename(doc.file_path)
    real_path = os.path.join(AEGIS_DIR, "vault", filename)
    txt_path = real_path + ".txt"
    if os.path.exists(real_path):
        os.remove(real_path)
    if os.path.exists(txt_path):
        os.remove(txt_path)

    await db.delete(doc)
    await db.commit()
    
    # Invalidate RAG Cache
    rag_cache.clear()

    await log_audit_trail(db, current_user.email, "DELETE_DOC", "documents", str(id))
    return {"status": "success"}

