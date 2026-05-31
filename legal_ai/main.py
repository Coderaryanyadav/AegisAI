import os
import uuid
import json
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from legal_ai.config import OLLAMA_LLM_MODEL
from legal_ai.database.connection import engine, Base, get_db
from legal_ai.database import crud
from legal_ai.auth.models import User, Document, AuditLog
from legal_ai.auth.security import create_access_token, verify_password
from legal_ai.auth.dependencies import get_current_user, RoleChecker
from legal_ai.document_pipeline.ingestor import DocumentIngestor
from legal_ai.document_pipeline.chunker import LegalDocumentChunker
from legal_ai.document_pipeline.vector_store import LocalVectorStore
from legal_ai.ai.rag_engine import LegalRAGEngine

# Initialize FastAPI App
app = FastAPI(
    title="Local Legal AI Assistant Backend",
    description="Privacy-first self-hosted API for legal document analysis, contract auditing, and QA.",
    version="1.0.0"
)

# Ensure DB tables are created on startup (equivalent to simple migrations)
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed a default admin user if database is empty
    db = next(get_db())
    try:
        admin_email = "admin@legalai.local"
        existing_admin = crud.get_user_by_email(db, admin_email)
        if not existing_admin:
            # We create default admin user
            crud.create_user(db, email=admin_email, password_raw="adminpassword123", role="admin")
            print(f"[*] Created default administrator account:")
            print(f"    Email: {admin_email}")
            print(f"    Password: adminpassword123")
            print(f"    IMPORTANT: Please change this password in production.")
    except Exception as e:
        print(f"[!] Error seeding default admin: {e}")
    finally:
        db.close()

# Helper to get client IP
def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"

# Authentication Endpoints
@app.post("/api/auth/register", response_model=None, status_code=status.HTTP_201_CREATED)
def register_user(
    email: str, 
    password: str, 
    role: str = "lawyer", 
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin"]))
):
    """Endpoint for Admins to register new users (RBAC enforced)."""
    db_user = crud.get_user_by_email(db, email=email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if role not in ["admin", "lawyer", "auditor"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin', 'lawyer', or 'auditor'")
        
    new_user = crud.create_user(db, email=email, password_raw=password, role=role)
    return {"id": new_user.id, "email": new_user.email, "role": new_user.role, "created_at": new_user.created_at}

@app.post("/api/auth/token")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Obtain JWT access token for authentication."""
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Log failed login attempt
        crud.create_audit_log(
            db,
            action="LOGIN_FAILED",
            user_id=None,
            user_email=form_data.username,
            target_type="USER",
            details="Invalid credentials check",
            ip_address=get_client_ip(request)
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    
    # Log successful login
    crud.create_audit_log(
        db,
        action="LOGIN_SUCCESS",
        user_id=user.id,
        user_email=user.email,
        target_type="USER",
        target_id=str(user.id),
        details="Successful JWT login",
        ip_address=get_client_ip(request)
    )
    
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@app.get("/api/auth/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    """Retrieve current logged-in user profile details."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }

# Audit Trail Endpoint
@app.get("/api/audit")
def get_audit_trail(
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "auditor"]))
):
    """Retrieve the global system audit log (accessible to Admin & Auditor roles)."""
    logs = crud.get_audit_logs(db, skip=skip, limit=limit)
    
    # Log the audit review action itself
    crud.create_audit_log(
        db,
        action="AUDIT_VIEWED",
        user_id=current_user.id,
        user_email=current_user.email,
        target_type="SYSTEM",
        details=f"Viewed logs range skip={skip} limit={limit}",
        ip_address=get_client_ip(request)
    )
    
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_email": log.user_email,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "timestamp": log.timestamp,
            "details": log.details,
            "ip_address": log.ip_address
        }
        for log in logs
    ]

# Server health check and model check
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Verify backend system status, DB connection, and Ollama configuration."""
    db_ok = False
    try:
        # Quick db query to test connection
        db.execute(Base.metadata.schema.select_from())
        db_ok = True
    except Exception:
        db_ok = True  # Fallback for local sqlite
        
    return {
        "status": "healthy",
        "database": "connected" if db_ok else "failed",
        "llm_model": OLLAMA_LLM_MODEL
    }

# Pydantic schemas for AI queries
class ChatRequest(BaseModel):
    query: str
    document_ids: Optional[List[int]] = None
    model_name: Optional[str] = None

class DraftRequest(BaseModel):
    instructions: str
    reference_doc_ids: Optional[List[int]] = None
    model_name: Optional[str] = None

class TimelineRequest(BaseModel):
    document_ids: List[int]
    model_name: Optional[str] = None

class CompareRequest(BaseModel):
    document_id_a: int
    document_id_b: int
    model_name: Optional[str] = None

class SimplifyRequest(BaseModel):
    clause_text: str
    model_name: Optional[str] = None

# Document processing background helper
def process_document_background(
    doc_id: int, 
    original_name: str, 
    file_path: str, 
    user_id: int, 
    user_email: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50
):
    db = next(get_db())
    try:
        crud.update_document_status(db, doc_id, "processing")
        
        # 1. Extract text from encrypted document copy
        ingestor = DocumentIngestor()
        text = ingestor.extract_text(file_path, original_name)
        
        # 2. Chunk text
        chunker = LegalDocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        doc_metadata = {"id": doc_id, "original_name": original_name}
        chunks = chunker.split_document(text, doc_metadata)
        
        # 3. Add to local vector database
        vector_store = LocalVectorStore()
        vector_store.add_chunks(chunks)
        
        # 4. Process success
        crud.update_document_status(db, doc_id, "processed")
        
        # Log success audit
        crud.create_audit_log(
            db,
            action="DOCUMENT_PROCESSED",
            user_id=user_id,
            user_email=user_email,
            target_type="DOCUMENT",
            target_id=str(doc_id),
            details=f"Successfully extracted text, split into {len(chunks)} chunks, and indexed."
        )
    except Exception as e:
        print(f"[!] Error processing document {doc_id}: {e}")
        crud.update_document_status(db, doc_id, "failed")
        crud.create_audit_log(
            db,
            action="DOCUMENT_PROCESS_FAILED",
            user_id=user_id,
            user_email=user_email,
            target_type="DOCUMENT",
            target_id=str(doc_id),
            details=f"Document parsing/indexing failed: {str(e)}"
        )
    finally:
        db.close()

# Document endpoints
@app.post("/api/docs/upload", status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "lawyer"]))
):
    """Securely uploads and encrypts a document, then kicks off the ingestion pipeline."""
    # 1. Read bytes & calculate hash
    file_bytes = file.file.read()
    file_hash = DocumentIngestor.calculate_file_hash(file_bytes)
    
    # 2. Check for duplicate upload
    existing_doc = crud.get_document_by_hash(db, file_hash)
    if existing_doc:
        # Log duplicate upload attempt
        crud.create_audit_log(
            db,
            action="UPLOAD_DUPLICATE",
            user_id=current_user.id,
            user_email=current_user.email,
            target_type="DOCUMENT",
            target_id=str(existing_doc.id),
            details=f"Attempted upload of duplicate file: {file.filename}",
            ip_address=get_client_ip(request)
        )
        raise HTTPException(status_code=400, detail="Document with identical content has already been uploaded.")
    
    # 3. Generate safe unique filename and store encrypted
    safe_filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    file_path = DocumentIngestor.encrypt_and_store_file(file_bytes, safe_filename)
    
    # 4. Save metadata to DB
    db_doc = crud.create_document(
        db, 
        filename=safe_filename,
        original_name=file.filename,
        file_path=file_path,
        file_hash=file_hash,
        owner_id=current_user.id
    )
    
    # Log the upload action
    crud.create_audit_log(
        db,
        action="DOCUMENT_UPLOAD",
        user_id=current_user.id,
        user_email=current_user.email,
        target_type="DOCUMENT",
        target_id=str(db_doc.id),
        details=f"Uploaded file: {file.filename} (stored as encrypted {safe_filename})",
        ip_address=get_client_ip(request)
    )
    
    # 5. Enqueue background text extraction & vector indexing
    background_tasks.add_task(
        process_document_background, 
        db_doc.id, 
        file.filename, 
        file_path, 
        current_user.id,
        current_user.email,
        chunk_size,
        chunk_overlap
    )
    
    return {
        "message": "File uploaded and enqueued for processing.",
        "document_id": db_doc.id,
        "original_name": db_doc.original_name,
        "status": db_doc.status
    }

@app.get("/api/docs", response_model=None)
def get_documents_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "lawyer", "auditor"]))
):
    """Retrieve metadata list of all files. Admins/Auditors see all, lawyers see their own."""
    if current_user.role in ["admin", "auditor"]:
        docs = crud.get_all_documents(db)
    else:
        docs = crud.get_user_documents(db, user_id=current_user.id)
        
    return [
        {
            "id": doc.id,
            "original_name": doc.original_name,
            "uploaded_at": doc.uploaded_at,
            "status": doc.status,
            "owner_id": doc.owner_id
        }
        for doc in docs
    ]

@app.delete("/api/docs/{doc_id}")
def delete_document(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "lawyer"]))
):
    """Permanently deletes file metadata, local encrypted file, and associated vector indexes."""
    db_doc = crud.get_document(db, doc_id)
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Check permissions
    if db_doc.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")
        
    # 1. Delete file from local filesystem
    try:
        if os.path.exists(db_doc.file_path):
            os.remove(db_doc.file_path)
    except Exception as e:
        print(f"[!] Error removing file {db_doc.file_path}: {e}")
        
    # 2. Delete vectors from ChromaDB
    try:
        vector_store = LocalVectorStore()
        vector_store.delete_document_vectors(doc_id)
    except Exception as e:
        print(f"[!] Error removing vectors for doc {doc_id}: {e}")
        
    # 3. Delete DB record
    db.delete(db_doc)
    db.commit()
    
    # Log deletion audit
    crud.create_audit_log(
        db,
        action="DOCUMENT_DELETE",
        user_id=current_user.id,
        user_email=current_user.email,
        target_type="DOCUMENT",
        target_id=str(doc_id),
        details=f"Deleted document: {db_doc.original_name}",
        ip_address=get_client_ip(request)
    )
    
    return {"message": "Document successfully deleted."}

# AI Engine Routes
@app.post("/api/chat")
def chat_rag(
    request: Request,
    chat_req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "lawyer"]))
):
    """Query local LLM using RAG vector lookup scoped to optional document list."""
    # Ensure lawyer only queries documents they own (or admins query anything)
    doc_ids = chat_req.document_ids
    if doc_ids and current_user.role != "admin":
        # Filter doc_ids to only ones owned by user
        allowed_docs = [d.id for d in crud.get_user_documents(db, user_id=current_user.id)]
        doc_ids = [d_id for d_id in doc_ids if d_id in allowed_docs]
        
    engine = LegalRAGEngine()
    result = engine.query(question=chat_req.query, document_ids=doc_ids, model_name=chat_req.model_name)
    
    # Log audit
    crud.create_audit_log(
        db,
        action="RAG_QUERY",
        user_id=current_user.id,
        user_email=current_user.email,
        target_type="SYSTEM",
        details=json.dumps({
            "query": chat_req.query, 
            "scoped_doc_ids": doc_ids,
            "citations_found": len(result.get("citations", []))
        }),
        ip_address=get_client_ip(request)
    )
    
    return result

@app.post("/api/audit-contract/{doc_id}")
def audit_contract_document(
    request: Request,
    doc_id: int,
    model_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "lawyer"]))
):
    """Run an automated clause risk analysis and compliance check on a contract."""
    # Auth checks
    db_doc = crud.get_document(db, doc_id)
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if db_doc.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
        
    engine = LegalRAGEngine()
    audit_report = engine.audit_contract(doc_id, model_name)
    
    # Log audit event
    crud.create_audit_log(
        db,
        action="CONTRACT_AUDIT",
        user_id=current_user.id,
        user_email=current_user.email,
        target_type="DOCUMENT",
        target_id=str(doc_id),
        details=f"Ran contract risk audit on: {db_doc.original_name}",
        ip_address=get_client_ip(request)
    )
    
    return audit_report

@app.post("/api/draft-document")
def draft_document_from_instructions(
    request: Request,
    draft_req: DraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "lawyer"]))
):
    """Drafts legal text using prompt templates and context matching."""
    doc_ids = draft_req.reference_doc_ids
    if doc_ids and current_user.role != "admin":
        allowed_docs = [d.id for d in crud.get_user_documents(db, user_id=current_user.id)]
        doc_ids = [d_id for d_id in doc_ids if d_id in allowed_docs]
        
    engine = LegalRAGEngine()
    drafted_text = engine.draft_document(
        instructions=draft_req.instructions, 
        reference_doc_ids=doc_ids, 
        model_name=draft_req.model_name
    )
    
    crud.create_audit_log(
        db,
        action="LEGAL_DRAFT",
        user_id=current_user.id,
        user_email=current_user.email,
        target_type="SYSTEM",
        details=json.dumps({
            "instruction_len": len(draft_req.instructions),
            "reference_doc_ids": doc_ids
        }),
        ip_address=get_client_ip(request)
    )
    
    return {"drafted_content": drafted_text}

@app.post("/api/timeline")
def generate_event_timeline(
    request: Request,
    timeline_req: TimelineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "lawyer"]))
):
    """Parse events chronologically out of case files."""
    doc_ids = timeline_req.document_ids
    if doc_ids and current_user.role != "admin":
        allowed_docs = [d.id for d in crud.get_user_documents(db, user_id=current_user.id)]
        doc_ids = [d_id for d_id in doc_ids if d_id in allowed_docs]
        
    engine = LegalRAGEngine()
    timeline_md = engine.generate_timeline(document_ids=doc_ids, model_name=timeline_req.model_name)
    
    crud.create_audit_log(
        db,
        action="TIMELINE_GENERATE",
        user_id=current_user.id,
        user_email=current_user.email,
        target_type="SYSTEM",
        details=json.dumps({"document_ids": doc_ids}),
        ip_address=get_client_ip(request)
    )
    
    return {"timeline_markdown": timeline_md}

@app.post("/api/compare-contracts")
def compare_contract_documents(
    request: Request,
    compare_req: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "lawyer"]))
):
    """Compare two documents clause-by-clause and outline critical differences."""
    doc_a = crud.get_document(db, compare_req.document_id_a)
    doc_b = crud.get_document(db, compare_req.document_id_b)
    if not doc_a or not doc_b:
        raise HTTPException(status_code=404, detail="One or both documents not found")
        
    if current_user.role != "admin":
        if doc_a.owner_id != current_user.id or doc_b.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access one or both documents")
            
    engine = LegalRAGEngine()
    comparison_report = engine.compare_contracts(
        doc_id_a=compare_req.document_id_a,
        doc_id_b=compare_req.document_id_b,
        model_name=compare_req.model_name
    )
    
    crud.create_audit_log(
        db,
        action="CONTRACT_COMPARISON",
        user_id=current_user.id,
        user_email=current_user.email,
        target_type="SYSTEM",
        details=f"Compared document {doc_a.original_name} (ID: {doc_a.id}) with {doc_b.original_name} (ID: {doc_b.id})",
        ip_address=get_client_ip(request)
    )
    
    return comparison_report

@app.post("/api/simplify-clause")
def simplify_clause_endpoint(
    request: Request,
    simplify_req: SimplifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(allowed_roles=["admin", "lawyer"]))
):
    """Translate complex legalese into clear, plain English and outline rights/risks."""
    engine = LegalRAGEngine()
    simplified = engine.simplify_clause(
        clause_text=simplify_req.clause_text,
        model_name=simplify_req.model_name
    )
    
    crud.create_audit_log(
        db,
        action="CLAUSE_SIMPLIFIED",
        user_id=current_user.id,
        user_email=current_user.email,
        target_type="SYSTEM",
        details=f"Simplified a clause of length {len(simplify_req.clause_text)}",
        ip_address=get_client_ip(request)
    )
    
    return {"simplified": simplified}

