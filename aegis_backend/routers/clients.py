import os
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

logger = logging.getLogger("aegis_ai.backend")

from aegis_backend.database import get_db, User, Client, Matter, Document
from aegis_backend.schemas.models import ClientCreate, ClientResponse
from aegis_backend.core.security import get_current_user, verify_lawyer_or_admin, verify_offline_mode, log_audit_trail
from aegis_backend.core.cache import rag_cache
from aegis_backend.vector_store import vector_store

router = APIRouter(tags=["clients"])

async def cleanup_matter_documents(matter_id: int, db: AsyncSession):
    stmt = select(Document).filter(Document.matter_id == matter_id)
    res = await db.execute(stmt)
    docs = res.scalars().all()
    for doc in docs:
        try:
            vector_store.delete_document_vectors(doc.id)
        except Exception as e:
            logger.warning(f"Error removing vectors for doc {doc.id} during matter deletion: {e}")
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        if os.path.exists(doc.file_path + ".txt"):
            os.remove(doc.file_path + ".txt")
        await db.delete(doc)

@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(response: Response, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "client":
        count_stmt = select(func.count(Client.id)).filter(Client.email == current_user.email)
        stmt = select(Client).filter(Client.email == current_user.email)
    else:
        count_stmt = select(func.count(Client.id))
        stmt = select(Client)
        
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar()
    response.headers["X-Total-Count"] = str(total_count)
    
    res = await db.execute(stmt.offset(skip).limit(limit))
    return res.scalars().all()

@router.post("/clients", response_model=ClientResponse)
async def create_client(client_in: ClientCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    client = Client(
        name=client_in.name,
        email=client_in.email,
        phone=client_in.phone,
        notes=client_in.notes
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    await log_audit_trail(db, current_user.email, "CREATE", "clients", str(client.id))
    return client

@router.delete("/clients/{id}")
async def delete_client(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    stmt = select(Client).filter(Client.id == id)
    res = await db.execute(stmt)
    client = res.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Cascade clean documents, files, and vectors of all matters belonging to this client
    stmt_matters = select(Matter).filter(Matter.client_id == id)
    res_matters = await db.execute(stmt_matters)
    matters = res_matters.scalars().all()
    for matter in matters:
        await cleanup_matter_documents(matter.id, db)

    await db.delete(client)
    await db.commit()

    # Invalidate RAG Cache
    rag_cache.clear()

    await log_audit_trail(db, current_user.email, "DELETE", "clients", str(id))
    return {"status": "success"}

