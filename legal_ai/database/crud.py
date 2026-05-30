import json
from sqlalchemy.orm import Session
from legal_ai.auth.models import User, Document, AuditLog
from legal_ai.auth.security import get_password_hash

# User CRUD
def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, email: str, password_raw: str, role: str = "lawyer"):
    hashed_password = get_password_hash(password_raw)
    db_user = User(
        email=email,
        hashed_password=hashed_password,
        role=role,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log this user creation audit event
    create_audit_log(
        db,
        action="USER_REGISTER",
        user_id=None,  # Or the registerer's ID if done by admin
        user_email="system",
        target_type="USER",
        target_id=str(db_user.id),
        details=json.dumps({"email": email, "role": role})
    )
    
    return db_user

# Audit Log CRUD
def create_audit_log(
    db: Session,
    action: str,
    user_id: int = None,
    user_email: str = None,
    target_type: str = None,
    target_id: str = None,
    details: str = None,
    ip_address: str = None
):
    log = AuditLog(
        user_id=user_id,
        user_email=user_email,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip_address
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_audit_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

# Document CRUD
def create_document(
    db: Session,
    filename: str,
    original_name: str,
    file_path: str,
    file_hash: str,
    owner_id: int
):
    db_doc = Document(
        filename=filename,
        original_name=original_name,
        file_path=file_path,
        file_hash=file_hash,
        owner_id=owner_id,
        status="pending"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

def get_document(db: Session, doc_id: int):
    return db.query(Document).filter(Document.id == doc_id).first()

def get_document_by_hash(db: Session, file_hash: str):
    return db.query(Document).filter(Document.file_hash == file_hash).first()

def update_document_status(db: Session, doc_id: int, status: str):
    db_doc = get_document(db, doc_id)
    if db_doc:
        db_doc.status = status
        db.commit()
        db.refresh(db_doc)
    return db_doc

def get_all_documents(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Document).offset(skip).limit(limit).all()

def get_user_documents(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(Document).filter(Document.owner_id == user_id).offset(skip).limit(limit).all()
