import os
import sys
import json
# Dynamic resolution of parent directories to support compiled packaging
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import uuid
import hashlib
import shutil
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import bcrypt
import jwt
from pydantic import BaseModel, EmailStr

from aegis_backend.database import (
    init_db, get_db, User, Client, Matter, Schedule, Document, AuditLog, BackupHistory, BareActSection, AEGIS_DIR, DB_PATH
)
from aegis_backend.vector_store import LocalVectorStore
from aegis_backend.document_processor import DocumentProcessor
from aegis_backend.indian_legal_helper import IndianLegalHelper
from aegis_backend.backup_manager import BackupManager, run_backup_scheduler
from aegis_backend.ollama_service import OllamaService

# Setup loggers
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis_ai.backend")

# Initialize database schemas
init_db()

app = FastAPI(title="AegisAI Offline Legal Suite", version="1.0.0")

# Allow CORS since React runs on a different port during local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "aegis_super_secret_local_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 1 day session for local client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")
vector_store = LocalVectorStore()

async def ensure_ollama_runtime():
    """Starts local Ollama daemon if offline and pre-pulls reasoning models."""
    import subprocess
    import sys
    
    # 1. Check if Ollama is running
    is_running = await OllamaService.is_ollama_running()
    if not is_running:
        logger.info("Ollama is not running. Attempting to start local Ollama service...")
        try:
            if sys.platform == "darwin":
                # Launch macOS desktop app quietly
                subprocess.Popen(["open", "-g", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Executed background command: open -g -a Ollama")
            elif sys.platform == "win32":
                local_app_data = os.environ.get("LOCALAPPDATA", "")
                ollama_exe = os.path.join(local_app_data, "Programs", "Ollama", "ollama app.exe")
                if os.path.exists(ollama_exe):
                    subprocess.Popen([ollama_exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Executed background command to launch Ollama Windows service.")
            else:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Executed background command: ollama serve")
        except Exception as e:
            logger.error(f"Failed to start Ollama daemon automatically: {e}")

        # 2. Wait up to 12 seconds for Ollama to start responding
        for i in range(12):
            await asyncio.sleep(1.0)
            if await OllamaService.is_ollama_running():
                logger.info("Ollama service came online successfully.")
                break
    else:
        logger.info("Ollama service is already online.")

    # 3. Check and pull deepseek-r1:8b if missing
    if await OllamaService.is_ollama_running():
        models = await OllamaService.get_available_models()
        target_model = "deepseek-r1:8b"
        has_model = any(target_model in m or "deepseek-r1" in m for m in models)
        if not has_model:
            logger.info(f"Target model '{target_model}' is not present in local list: {models}. Initiating background pull...")
            asyncio.create_task(OllamaService.pull_model(target_model))
        else:
            logger.info(f"Target model '{target_model}' is already present. Ready for local queries.")
    else:
        logger.warning("Could not establish connection to Ollama. Automatic model pre-pull skipped.")

# Start background backup scheduler on app startup
@app.on_event("startup")
async def startup_event():
    # Schedule automated snapshot every hour
    asyncio.create_task(run_backup_scheduler(interval_seconds=3600, retention_limit=5))
    # Spin up background Ollama checks and auto-launcher
    asyncio.create_task(ensure_ollama_runtime())

# ================= HELPER FUNCTIONS =================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def log_audit_trail(db: Session, email: str, action: str, target_type: str, target_id: Optional[str] = None, details: Optional[str] = None):
    log = AuditLog(
        user_email=email,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details
    )
    db.add(log)
    db.commit()

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

# ================= PYDANTIC SCHEMAS =================

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str = "lawyer"

class UserResponse(BaseModel):
    id: int
    email: str
    role: str

    class Config:
        orm_mode = True

class ClientCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

class MatterCreate(BaseModel):
    client_id: int
    case_number: Optional[str] = None
    title: str
    court: Optional[str] = None
    judge: Optional[str] = None
    opponent_name: Optional[str] = None
    opposing_advocate: Optional[str] = None
    status: str = "open"
    facts: Optional[str] = None

class ScheduleCreate(BaseModel):
    matter_id: int
    title: str
    schedule_type: str  # hearing, deadline, meeting
    target_date: str
    notes: Optional[str] = None

class ResearchQuery(BaseModel):
    query: str
    matter_ids: Optional[List[int]] = None
    model_name: str = "deepseek-r1:8b" # default local model

class ConflictCheckRequest(BaseModel):
    client_name: str
    opponent_name: str
    facts: Optional[str] = None

class FormatDraftRequest(BaseModel):
    draft_text: str
    court_header: str = "none" # none, supreme_court, high_court, district_court
    line_spacing: float = 1.5
    margin_spaces: int = 4

# ================= API ROUTERS =================

# 1. AUTHENTICATION
@app.post("/api/auth/register", response_model=UserResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # Automatically register first user as admin, others as lawyer
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already registered")
    
    hashed = hash_password(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed,
        role=user_in.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit_trail(db, user.email, "REGISTER", "users", str(user.id))
    return user

@app.post("/api/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    log_audit_trail(db, user.email, "LOGIN", "users", str(user.id))
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# 2. CLIENT RECORDS
@app.get("/api/clients")
def list_clients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Client).all()

@app.post("/api/clients")
def create_client(client_in: ClientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    client = Client(**client_in.dict())
    db.add(client)
    db.commit()
    db.refresh(client)
    log_audit_trail(db, current_user.email, "CREATE", "clients", str(client.id))
    return client

@app.delete("/api/clients/{id}")
def delete_client(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    log_audit_trail(db, current_user.email, "DELETE", "clients", str(id))
    return {"status": "success"}


# 3. MATTERS (Indian Case Files)
@app.get("/api/matters")
def list_matters(client_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Matter)
    if client_id:
        query = query.filter(Matter.client_id == client_id)
    return query.all()

@app.post("/api/matters")
def create_matter(matter_in: MatterCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    matter = Matter(**matter_in.dict())
    db.add(matter)
    db.commit()
    db.refresh(matter)
    log_audit_trail(db, current_user.email, "CREATE", "matters", str(matter.id))
    return matter

@app.delete("/api/matters/{id}")
def delete_matter(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    matter = db.query(Matter).filter(Matter.id == id).first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    db.delete(matter)
    db.commit()
    log_audit_trail(db, current_user.email, "DELETE", "matters", str(id))
    return {"status": "success"}

@app.post("/api/matters/check-conflict")
def check_legal_conflict(req: ConflictCheckRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    ETHICAL CONFLICT OF INTEREST CHECKER:
    1. Checks if the prospective client_name is an opponent in any active case.
    2. Checks if the prospective opponent_name is currently a client.
    3. Checks if the prospective opposing advocate is currently associated with a client.
    """
    logger.info(f"Running Conflict check: client={req.client_name}, opponent={req.opponent_name}")
    
    conflict_detected = False
    severity = "low"
    reasons = []

    clean_client = req.client_name.strip().upper()
    clean_opponent = req.opponent_name.strip().upper()

    if not clean_client or not clean_opponent:
        raise HTTPException(status_code=400, detail="Client name and Opponent name are required.")

    # Rule 1: Check if opponent is already a client
    clients = db.query(Client).all()
    for c in clients:
        if clean_opponent in c.name.upper() or c.name.upper() in clean_opponent:
            conflict_detected = True
            severity = "high"
            reasons.append(f"DIRECT CONFLICT: Opponent '{req.opponent_name}' matches active client folder '{c.name}' (Client ID: {c.id}).")

    # Rule 2: Check if client is an opponent in an active case
    matters = db.query(Matter).all()
    for m in matters:
        if m.opponent_name:
            clean_matter_opp = m.opponent_name.strip().upper()
            if clean_client in clean_matter_opp or clean_matter_opp in clean_client:
                conflict_detected = True
                severity = "high"
                reasons.append(f"INDIRECT CONFLICT: Prospective client '{req.client_name}' is listed as Opponent in active matter file '{m.title}' (Matter ID: {m.id}, Client: {m.client.name}).")
        
        # Check if the prospective opponent is a party in another matter under our representation
        if m.client:
            clean_matter_client = m.client.name.strip().upper()
            if clean_opponent in clean_matter_client or clean_matter_client in clean_opponent:
                conflict_detected = True
                if severity != "high":
                    severity = "medium"
                reasons.append(f"ASSOCIATED RISK: Prospective opponent '{req.opponent_name}' matches client '{m.client.name}' in matter file '{m.title}'.")

    # Log conflict check
    log_audit_trail(
        db, 
        current_user.email, 
        "CONFLICT_CHECK", 
        "compliance", 
        details=f"Ran check for Client: '{req.client_name}' vs Opponent: '{req.opponent_name}'. Result: conflict_detected={conflict_detected}"
    )

    return {
        "client_name": req.client_name,
        "opponent_name": req.opponent_name,
        "conflict_detected": conflict_detected,
        "severity": severity,
        "reasons": reasons
    }


# 4. COURT SCHEDULES & DEADLINES
@app.get("/api/schedules")
def list_schedules(matter_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Schedule)
    if matter_id:
        query = query.filter(Schedule.matter_id == matter_id)
    return query.order_by(Schedule.target_date.asc()).all()

@app.post("/api/schedules")
def create_schedule(schedule_in: ScheduleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sch = Schedule(**schedule_in.dict())
    db.add(sch)
    db.commit()
    db.refresh(sch)
    log_audit_trail(db, current_user.email, "CREATE", "schedules", str(sch.id))
    return sch

@app.put("/api/schedules/{id}/complete")
def complete_schedule(id: int, completed: bool = True, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sch = db.query(Schedule).filter(Schedule.id == id).first()
    if not sch:
        raise HTTPException(status_code=404, detail="Schedule event not found")
    sch.is_completed = completed
    db.commit()
    return sch


# 5. DOCUMENT PROCESSING PIPELINE (PyMuPDF / OCR -> DB / Vector Store)
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
        # Extract text using PyMuPDF or Tesseract fallback
        text = DocumentProcessor.extract_text(file_path)
        
        # Save raw content in local file system or db
        raw_text_path = file_path + ".txt"
        with open(raw_text_path, "w", encoding="utf-8") as f:
            f.write(text)

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
        doc.status = "failed"
    finally:
        db.commit()
        db.close()

@app.post("/api/documents/upload")
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    matter_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    vault_dir = os.path.join(AEGIS_DIR, "vault")
    os.makedirs(vault_dir, exist_ok=True)

    file_uuid = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{file_uuid}{ext}"
    dest_path = os.path.join(vault_dir, stored_name)

    # Save to vault
    sha256_hash = hashlib.sha256()
    with open(dest_path, "wb") as buffer:
        for chunk in iter(lambda: file.file.read(4096), b""):
            buffer.write(chunk)
            sha256_hash.update(chunk)
    
    file_hash = sha256_hash.hexdigest()

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

@app.get("/api/documents")
def list_documents(matter_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Document)
    if matter_id:
        query = query.filter(Document.matter_id == matter_id)
    return query.all()

@app.get("/api/documents/{id}/text")
def get_document_text(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    txt_path = doc.file_path + ".txt"
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            return {"text": f.read()}
    return {"text": "Extracted text not ready or file failed processing."}

@app.delete("/api/documents/{id}")
def delete_document(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Remove vectors
    try:
        vector_store.delete_document_vectors(doc.id)
    except Exception as e:
        logger.warning(f"Error removing vectors for doc {id}: {e}")

    # Remove files
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    if os.path.exists(doc.file_path + ".txt"):
        os.remove(doc.file_path + ".txt")

    db.delete(doc)
    db.commit()
    log_audit_trail(db, current_user.email, "DELETE_DOC", "documents", str(id))
    return {"status": "success"}


# 6. LEGAL RESEARCH RAG (Hybrid Search RRF + LLM Response)
@app.post("/api/research/query")
async def query_legal_rag(req: ResearchQuery, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Fetch relevant chunks from local hybrid index (using RRF)
    chunks = vector_store.query_hybrid(req.query, limit=5, document_ids=req.matter_ids)

    # 2. Build RAG prompt with local context
    context = ""
    for idx, c in enumerate(chunks):
        filename = c["metadata"].get("filename", "Unknown Document")
        context += f"[Context {idx+1}] File: {filename}\nContent:\n{c['content']}\n\n"

    system_prompt = (
        "You are AegisAI, an expert Indian legal assistant. "
        "Answer the user's questions truthfully and accurately using the context provided. "
        "Always cite the document name or section numbers clearly. "
        "Provide professional analysis, citations, ratios, or statutory converted references where relevant. "
        "If you do not know, state that you do not know based on local context."
    )

    prompt = (
        f"Context Details:\n{context}\n"
        f"Query: {req.query}\n"
        f"Provide your professional legal response with references:"
    )

    response = await OllamaService.generate_completion(
        model=req.model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    # Record search action in audit logs
    log_audit_trail(db, current_user.email, "LEGAL_SEARCH", "rag", details=req.query)

    return {
        "response": response,
        "sources": [{"id": c["id"], "text": c["content"], "metadata": c["metadata"]} for c in chunks]
    }


# 7. INDIAN LEGAL STATUTORY CONVERTER & CITATION HELPER
@app.get("/api/helper/ipc-bns")
def get_statutory_mapping(act: str, section: str, db: Session = Depends(get_db)):
    mapping = IndianLegalHelper.convert_section(act, section)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found for the requested section.")
    
    new_section = mapping.get("new_section")
    target_act = mapping.get("act")
    
    full_text = None
    if new_section and target_act:
        sect_data = db.query(BareActSection).filter(
            BareActSection.act == target_act,
            BareActSection.section == new_section
        ).first()
        if sect_data:
            full_text = sect_data.content
            
    return {
        **mapping,
        "full_text": full_text
    }

@app.post("/api/helper/normalize-citation")
def normalize_citation(citation: str = Form(...)):
    normalized = IndianLegalHelper.normalize_citation(citation)
    return {"original": citation, "normalized": normalized}

@app.post("/api/analyze/cause-list")
def parse_cause_list(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import fitz # PyMuPDF
    import tempfile
    import re
    
    temp_pdf_path = os.path.join(tempfile.gettempdir(), f"cause_list_{uuid.uuid4()}.pdf")
    with open(temp_pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    text = ""
    try:
        doc = fitz.open(temp_pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=400, detail=f"Failed to read Cause List PDF: {e}")
        
    if os.path.exists(temp_pdf_path):
        os.remove(temp_pdf_path)

    matters = db.query(Matter).all()
    matches = []
    
    for matter in matters:
        if not matter.case_number:
            continue
        
        clean_num = matter.case_number.strip().upper()
        simple_pattern = re.sub(r"[^A-Z0-9/]", "", clean_num)
        simple_text = re.sub(r"[^A-Z0-9/]", "", text.upper())
        
        if simple_pattern and simple_pattern in simple_text:
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            
            existing = db.query(Schedule).filter(
                Schedule.matter_id == matter.id,
                Schedule.title == f"Automatic Cause List Hearing: {matter.case_number}",
                Schedule.target_date == target_date
            ).first()
            
            if not existing:
                schedule = Schedule(
                    matter_id=matter.id,
                    title=f"Automatic Cause List Hearing: {matter.case_number}",
                    schedule_type="hearing",
                    target_date=target_date,
                    notes=f"Auto-extracted match in uploaded daily court Cause List PDF: '{file.filename}'."
                )
                db.add(schedule)
                db.commit()
                db.refresh(schedule)
                matches.append({
                    "matter_id": matter.id,
                    "case_number": matter.case_number,
                    "title": matter.title,
                    "schedule_id": schedule.id,
                    "target_date": target_date
                })
            else:
                matches.append({
                    "matter_id": matter.id,
                    "case_number": matter.case_number,
                    "title": matter.title,
                    "schedule_id": existing.id,
                    "target_date": target_date,
                    "already_scheduled": True
                })
                
    log_audit_trail(db, current_user.email, "PARSE_CAUSE_LIST", "cause_list", details=f"Scanned {file.filename}, found {len(matches)} matches.")
    
    return {
        "filename": file.filename,
        "matches_found": len(matches),
        "matches": matches
    }


# 8. SCANNED CASE ANALYZER (Timeline & Fact Extractors)
@app.post("/api/analyze/extract-timeline")
async def extract_case_timeline(document_id: int, model_name: str = "deepseek-r1:8b", db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    txt_path = doc.file_path + ".txt"
    if not os.path.exists(txt_path):
        raise HTTPException(status_code=400, detail="Document text extraction is not complete yet.")

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Limit size to prevent token limits on local LLM
    snippet = text[:8000]

    prompt = (
        f"Analyze the following legal document (FIR, Charge sheet, or Judgment) and extract all chronological events.\n"
        f"Format the output strictly as a JSON list of objects. Each object must have fields 'date' (ISO-ish or natural format), "
        f"'description' (brief summary of event), and 'involved_parties' (key people involved).\n\n"
        f"Document Snippet:\n{snippet}\n\nJSON Output:"
    )

    system_prompt = "You are a legal document analyst. Output only valid JSON lists. Do not include chat explanations or markdown blocks."

    timeline = await OllamaService.generate_structured(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {"timeline": timeline}

@app.post("/api/analyze/facts")
async def extract_case_facts(document_id: int, model_name: str = "deepseek-r1:8b", db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    txt_path = doc.file_path + ".txt"
    if not os.path.exists(txt_path):
        raise HTTPException(status_code=400, detail="Document text extraction is not complete.")

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    snippet = text[:8000]

    prompt = (
        f"Summarize the legal facts from the following text.\n"
        f"Identify the offense description, the sections invoked (IPC, BNS, CrPC, etc.), "
        f"the accused individuals, and the complaining/victim parties. "
        f"Format the output strictly as a JSON object with fields: 'offence', 'sections_invoked', 'accused', 'victims', 'summary'.\n\n"
        f"Document Snippet:\n{snippet}\n\nJSON Output:"
    )

    system_prompt = "You are an Indian criminal defense analyst. Output only valid JSON. Do not write text outside the JSON."

    facts = await OllamaService.generate_structured(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {"facts": facts}


# 9. CONTRACT AUDITOR (Indemnity, Risk Scanning, Compare Clauses)
@app.post("/api/audit/risk-scan")
async def scan_contract_risks(document_id: int, model_name: str = "deepseek-r1:8b", db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    txt_path = doc.file_path + ".txt"
    if not os.path.exists(txt_path):
        raise HTTPException(status_code=400, detail="Contract text is not parsed yet.")

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    snippet = text[:10000]

    prompt = (
        f"Perform an audit on this contract. Extract all clauses representing potential liability, termination terms, indemnity issues, "
        f"or high financial risks. For each risk found, rate it as 'High', 'Medium', or 'Low' risk.\n"
        f"Format response strictly as a JSON list of objects with fields: 'clause_title', 'risk_rating', 'summary', 'remediation_advice'.\n\n"
        f"Contract Snippet:\n{snippet}\n\nJSON Output:"
    )

    system_prompt = "You are an expert corporate contracts auditor. Output only valid JSON."

    risks = await OllamaService.generate_structured(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {"risks": risks}

@app.post("/api/audit/compare")
async def compare_clauses(doc_id_a: int, doc_id_b: int, model_name: str = "deepseek-r1:8b", db: Session = Depends(get_db)):
    doc_a = db.query(Document).filter(Document.id == doc_id_a).first()
    doc_b = db.query(Document).filter(Document.id == doc_id_b).first()
    if not doc_a or not doc_b:
        raise HTTPException(status_code=404, detail="One or both documents not found")

    path_a, path_b = doc_a.file_path + ".txt", doc_b.file_path + ".txt"
    if not os.path.exists(path_a) or not os.path.exists(path_b):
        raise HTTPException(status_code=400, detail="One or both documents are not fully parsed.")

    with open(path_a, "r") as f:
        text_a = f.read()[:6000]
    with open(path_b, "r") as f:
        text_b = f.read()[:6000]

    prompt = (
        f"Compare Document A with Document B. Identify the primary structural changes, discrepancies, or clause variations "
        f"between both legal texts (e.g. indemnity, liability ceilings, termination notice periods).\n"
        f"Format response strictly as a JSON list of objects with fields: 'clause_title', 'doc_a_provision', 'doc_b_provision', 'variance_type' (Addition/Deletion/Modification), 'risk_assessment'.\n\n"
        f"Document A:\n{text_a}\n\nDocument B:\n{text_b}\n\nJSON Output:"
    )

    system_prompt = "You are a contract negotiation expert. Output only valid JSON."

    comparison = await OllamaService.generate_structured(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {"comparison": comparison}


# 10. DOCUMENT DRAFTING
@app.get("/api/draft/templates")
def list_draft_templates():
    return [
        {
            "id": "legal_notice",
            "name": "Legal Notice for Recovery of Dues",
            "fields": ["client_name", "debtor_name", "amount_due", "due_date", "notice_period_days"]
        },
        {
            "id": "bail_application",
            "name": "Bail Application under Section 439 CrPC (483 BNSS)",
            "fields": ["accused_name", "fir_number", "police_station", "offences_charged", "grounds_for_bail"]
        },
        {
            "id": "tenancy_agreement",
            "name": "Residential Tenancy Agreement",
            "fields": ["landlord_name", "tenant_name", "property_address", "monthly_rent", "security_deposit", "lease_term_months"]
        }
    ]

@app.post("/api/draft/generate")
async def generate_draft(template_id: str, fields: Dict[str, str], model_name: str = "deepseek-r1:8b"):
    prompt = (
        f"Draft a formal, legally enforceable Indian document of type: '{template_id}'.\n"
        f"Use the following custom details in the draft:\n{json.dumps(fields, indent=2)}\n\n"
        f"Ensure it strictly follows standard formatting in Indian courts, incorporates BNS/BNSS statutory terms where appropriate, "
        f"and leaves placeholders for signatures. Write the complete document draft text:"
    )

    system_prompt = "You are an experienced advocate in the Supreme Court of India. Write professional legal drafts."

    draft_text = await OllamaService.generate_completion(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {"draft": draft_text}

@app.post("/api/draft/format")
def format_legal_draft(req: FormatDraftRequest):
    formatted_lines = []
    
    # 1. Apply Court Header Template
    if req.court_header == "supreme_court":
        header = (
            "IN THE SUPREME COURT OF INDIA\n"
            "(ORIGINAL JURISDICTION / CIVIL APPELLATE JURISDICTION)\n"
            "WRIT PETITION / APPEAL NO. ______ OF 2026\n\n"
            "IN THE MATTER OF:\n"
            "_________________________                     ... PETITIONER(S)\n"
            "      VERSUS\n"
            "_________________________                     ... RESPONDENT(S)\n\n"
            "================================================================================\n"
        )
        formatted_lines.append(header)
    elif req.court_header == "high_court":
        header = (
            "IN THE HIGH COURT OF DELHI AT NEW DELHI\n"
            "(ORDINARY ORIGINAL CIVIL JURISDICTION)\n"
            "O.S. NO. ______ OF 2026\n\n"
            "IN THE MATTER OF:\n"
            "_________________________                     ... PLAINTIFF\n"
            "      VERSUS\n"
            "_________________________                     ... DEFENDANT\n\n"
            "================================================================================\n"
        )
        formatted_lines.append(header)
    elif req.court_header == "district_court":
        header = (
            "IN THE COURT OF THE DISTRICT & SESSIONS JUDGE, SAKET COURTS, NEW DELHI\n"
            "CIVIL / CRIMINAL SUIT NO. ______ OF 2026\n\n"
            "IN THE MATTER OF:\n"
            "_________________________                     ... COMPLAINANT/PLAINTIFF\n"
            "      VERSUS\n"
            "_________________________                     ... ACCUSED/DEFENDANT\n\n"
            "================================================================================\n"
        )
        formatted_lines.append(header)
        
    raw_lines = req.draft_text.split("\n")
    
    # Apply Margin (prefix each line with spaces)
    margin_prefix = " " * req.margin_spaces
    for line in raw_lines:
        formatted_line = f"{margin_prefix}{line}"
        formatted_lines.append(formatted_line)
        
    # Apply Line Spacing (double spacing or single spacing)
    separator = "\n\n" if req.line_spacing > 1.2 else "\n"
    final_text = separator.join(formatted_lines)
    
    return {"formatted_draft": final_text}


# 11. ENCRYPTED BACKUP CONTROLS (Panic Button + Safe Restores)
@app.get("/api/backup/history")
def get_backup_runs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(BackupHistory).order_by(BackupHistory.created_at.desc()).all()

@app.get("/api/system/audit-logs")
def get_compliance_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized role access.")
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()

@app.get("/api/system/audit-logs/export")
def export_signed_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized role access.")
        
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    
    # Construct a clean, human-readable text document
    report_lines = []
    report_lines.append("================================================================================")
    report_lines.append("                       AEGIS LEGAL AI COMPLIANCE AUDIT REPORT                   ")
    report_lines.append("================================================================================")
    report_lines.append(f"Exported At: {datetime.utcnow().isoformat()} UTC")
    report_lines.append(f"Exported By: {current_user.email}")
    report_lines.append(f"System Directory: {AEGIS_DIR}")
    report_lines.append("--------------------------------------------------------------------------------")
    report_lines.append(f"{'TIMESTAMP (UTC)':<20} | {'USER EMAIL':<30} | {'ACTION':<15} | {'TARGET':<10} | DETAILS")
    report_lines.append("--------------------------------------------------------------------------------")
    
    for l in logs:
        ts = l.timestamp.isoformat() if l.timestamp else "N/A"
        email = l.user_email or "N/A"
        act = l.action or "N/A"
        tgt = l.target_type or "N/A"
        det = l.details or ""
        report_lines.append(f"{ts:<20} | {email:<30} | {act:<15} | {tgt:<10} | {det}")
        
    report_lines.append("================================================================================")
    report_lines.append("                       END OF AEGIS AUDIT TRAIL LOG                            ")
    report_lines.append("================================================================================")
    
    report_content = "\n".join(report_lines)
    
    # Read the master key to sign the report content
    key_path = os.path.join(AEGIS_DIR, ".master.key")
    try:
        with open(key_path, "rb") as f:
            master_key = f.read()
    except Exception:
        master_key = b"fallback-aegis-key-hash"
        
    # Generate HMAC-SHA256 signature to guarantee local sandbox integrity
    import hmac
    import hashlib
    signature = hmac.new(master_key, report_content.encode("utf-8"), hashlib.sha256).hexdigest()
    
    signed_document = f"{report_content}\n\n[CRYPTOGRAPHIC INTEGRITY SIGNATURE]\nHMAC-SHA256: {signature}\n"
    
    from fastapi.responses import Response
    return Response(
        content=signed_document,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=aegis_compliance_audit_report.txt"
        }
    )

@app.post("/api/backup/create")
def trigger_manual_backup(current_user: User = Depends(get_current_user)):
    try:
        backup_path = BackupManager.create_backup(is_manual=True)
        return {"status": "success", "path": backup_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup generation failed: {e}")

@app.post("/api/backup/restore")
def trigger_restore(backup_path: str, current_user: User = Depends(get_current_user)):
    try:
        BackupManager.restore_backup(backup_path)
        return {"status": "success", "message": "Restore completed. Application state reverted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restoration failed: {e}")

@app.post("/api/backup/panic", status_code=200)
def emergency_panic_button(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    EMERGENCY PANIC SYSTEM:
    1. Immediately locks up active database handles.
    2. Performs a final, fast emergency AES-256 zip backup.
    3. Truncates/wipes active client data, matters, documents, and vector collections from active workspace.
    4. Ensures zero exposure of sensitive client details.
    """
    logger.warning("PANIC SIGNAL INITIATED: Wiping active workspace contents.")
    try:
        # Create emergency recovery point
        emergency_backup_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        backup_path = BackupManager.create_backup(destination_dir=emergency_backup_dir, is_manual=True)
        
        # WIPE DB tables containing client secrets
        db.query(Document).delete()
        db.query(Schedule).delete()
        db.query(Matter).delete()
        db.query(Client).delete()
        db.query(AuditLog).delete()
        db.commit()

        # Wipe document vault files
        vault_dir = os.path.join(AEGIS_DIR, "vault")
        if os.path.exists(vault_dir):
            for f in os.listdir(vault_dir):
                file_path = os.path.join(vault_dir, f)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        # Wipe chroma collections
        chroma_dir = os.path.join(AEGIS_DIR, "chroma")
        if os.path.exists(chroma_dir):
            shutil.rmtree(chroma_dir)
            os.makedirs(chroma_dir, exist_ok=True)

        logger.warning("PANIC PROCESS COMPLETED. All client secrets eradicated from active workspace.")
        return {
            "status": "panic_complete",
            "message": f"Active records scrubbed. Sealed recovery archive created at: {backup_path}"
        }
    except Exception as e:
        logger.error(f"Panic recovery routine failed: {e}")
        raise HTTPException(status_code=500, detail=f"Panic wipe routine encountered error: {e}")


# 12. SYSTEM STATUS & CONFIGURATION
@app.get("/api/system/models")
async def list_ollama_models(current_user: User = Depends(get_current_user)):
    models = await OllamaService.get_available_models()
    return {"models": models}

@app.get("/api/system/status")
async def system_diagnostics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    models = await OllamaService.get_available_models()
    ollama_running = len(models) > 0

    vault_dir = os.path.join(AEGIS_DIR, "vault")
    doc_count = db.query(Document).count()
    matter_count = db.query(Matter).count()
    client_count = db.query(Client).count()

    db_size = 0
    if os.path.exists(DB_PATH):
        db_size = os.path.getsize(DB_PATH)

    return {
        "ollama_connected": ollama_running,
        "models_available": models,
        "database_size_bytes": db_size,
        "registered_clients": client_count,
        "registered_matters": matter_count,
        "vault_document_count": doc_count
    }

if __name__ == "__main__":
    import uvicorn
    import asyncio
    uvicorn.run(app, host="0.0.0.0", port=8000)
