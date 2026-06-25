import os
import uuid
import hashlib
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from aegis_backend.database import get_db, SessionLocal, User, Client, Matter, Document, AEGIS_DIR
from aegis_backend.schemas.models import DocumentResponse
from aegis_backend.core.security import get_current_user, verify_lawyer_or_admin, log_audit_trail, read_decrypted_document_text
from aegis_backend.vector_store import LocalVectorStore
from aegis_backend.document_processor import DocumentProcessor

router = APIRouter(prefix="/api", tags=["documents"])
vector_store = LocalVectorStore()
logger = logging.getLogger("aegis_ai.backend")

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

def process_uploaded_document_task(doc_id: int, file_path: str, db_session_factory):
    """Background task to extract and vector-index documents."""
    db = db_session_factory()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        db.close()
        return

    doc.status = "processing"
    db.commit()

    try:
        from aegis_backend.database import cipher
        import tempfile

        # Decrypt binary file
        with open(file_path, "rb") as enc_file:
            encrypted_data = enc_file.read()
        raw_data = cipher.decrypt(encrypted_data)

        if doc.original_name.lower().endswith(".txt"):
            text = raw_data.decode("utf-8", errors="ignore")
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(raw_data)
                tmp_path = tmp.name

            try:
                # Extract text using PyMuPDF or Tesseract fallback
                text = DocumentProcessor.extract_text(tmp_path)
            finally:
                os.remove(tmp_path)
        
        # Save raw content in local file system encrypted
        raw_text_path = file_path + ".txt"
        encrypted_text = cipher.encrypt(text.encode('utf-8'))
        with open(raw_text_path, "wb") as f:
            f.write(encrypted_text)

        # Chunk text
        chunks = chunk_text(text)
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
        logger.info(f"Processed and indexed document: {doc.original_name}")
    except Exception as e:
        logger.error(f"Failed to process document {doc_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        doc.status = "failed"
    finally:
        db.commit()
        db.close()

@router.post("/documents/upload", response_model=DocumentResponse)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    matter_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_lawyer_or_admin)
):
    vault_dir = os.path.join(AEGIS_DIR, "vault")
    os.makedirs(vault_dir, exist_ok=True)

    file_uuid = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{file_uuid}{ext}"
    dest_path = os.path.join(vault_dir, stored_name)

    # Enforce file size limit of 100MB to prevent OOM
    from aegis_backend.database import cipher
    raw_data = file.file.read()
    if len(raw_data) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 100MB.")
        
    sha256_hash = hashlib.sha256()
    sha256_hash.update(raw_data)
    file_hash = sha256_hash.hexdigest()

    encrypted_data = cipher.encrypt(raw_data)
    with open(dest_path, "wb") as buffer:
        buffer.write(encrypted_data)

    # Register in SQLite
    doc = Document(
        matter_id=matter_id,
        original_name=file.filename,
        stored_uuid=file_uuid,
        file_path=dest_path,
        file_hash=file_hash,
        status="uploaded"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_audit_trail(db, current_user.email, "UPLOAD_DOC", "documents", str(doc.id), file.filename)

    # Trigger background extractor and indexer
    background_tasks.add_task(process_uploaded_document_task, doc.id, dest_path, SessionLocal)

    return doc

@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(matter_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Document)
    if current_user.role == "client":
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if not client:
            return []
        mat_ids = [m.id for m in db.query(Matter).filter(Matter.client_id == client.id).all()]
        if matter_id and matter_id in mat_ids:
            query = query.filter(Document.matter_id == matter_id)
        else:
            query = query.filter(Document.matter_id.in_(mat_ids))
    elif matter_id:
        query = query.filter(Document.matter_id == matter_id)
    return query.offset(skip).limit(limit).all()

@router.get("/documents/{id}/text")
def get_document_text(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    filename = os.path.basename(doc.file_path)
    txt_path = os.path.join(AEGIS_DIR, "vault", filename + ".txt")
    if os.path.exists(txt_path):
        decrypted_text = read_decrypted_document_text(txt_path)
        return {"text": decrypted_text}
    return {"text": "Extracted text not ready or file failed processing."}

@router.delete("/documents/{id}")
def delete_document(id: int, db: Session = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
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

    db.delete(doc)
    db.commit()
    log_audit_trail(db, current_user.email, "DELETE_DOC", "documents", str(id))
    return {"status": "success"}
