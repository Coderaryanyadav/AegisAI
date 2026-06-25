import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from aegis_backend.database import get_db, User, Client, Matter, Document
from aegis_backend.schemas.models import ClientCreate, ClientResponse
from aegis_backend.core.security import get_current_user, verify_lawyer_or_admin, verify_offline_mode, log_audit_trail
from aegis_backend.vector_store import LocalVectorStore

router = APIRouter(prefix="/api", tags=["clients"])
vector_store = LocalVectorStore()

def cleanup_matter_documents(matter_id: int, db: Session):
    docs = db.query(Document).filter(Document.matter_id == matter_id).all()
    for doc in docs:
        try:
            vector_store.delete_document_vectors(doc.id)
        except Exception as e:
            import logging
            logging.getLogger("aegis_ai.backend").warning(f"Error removing vectors for doc {doc.id} during matter deletion: {e}")
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        if os.path.exists(doc.file_path + ".txt"):
            os.remove(doc.file_path + ".txt")
        db.delete(doc)

@router.get("/clients", response_model=List[ClientResponse])
def list_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "client":
        return db.query(Client).filter(Client.email == current_user.email).offset(skip).limit(limit).all()
    return db.query(Client).offset(skip).limit(limit).all()

@router.post("/clients", response_model=ClientResponse)
def create_client(client_in: ClientCreate, db: Session = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    client = Client(
        name=client_in.name,
        email=client_in.email,
        phone=client_in.phone,
        notes=client_in.notes
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    log_audit_trail(db, current_user.email, "CREATE", "clients", str(client.id))
    return client

@router.delete("/clients/{id}")
def delete_client(id: int, db: Session = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    client = db.query(Client).filter(Client.id == id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Cascade clean documents, files, and vectors of all matters belonging to this client
    matters = db.query(Matter).filter(Matter.client_id == id).all()
    for matter in matters:
        cleanup_matter_documents(matter.id, db)

    db.delete(client)
    db.commit()
    log_audit_trail(db, current_user.email, "DELETE", "clients", str(id))
    return {"status": "success"}
