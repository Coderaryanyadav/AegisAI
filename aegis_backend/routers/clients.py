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

from aegis_backend.services.client_service import ClientService

router = APIRouter(tags=["clients"])

@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(response: Response, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    clients, total_count = await ClientService.get_clients_list(db, current_user, skip, limit)
    response.headers["X-Total-Count"] = str(total_count)
    return clients

@router.post("/clients", response_model=ClientResponse)
async def create_client(client_in: ClientCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    client = await ClientService.create_client(db, client_in)
    await log_audit_trail(db, current_user.email, "CREATE", "clients", str(client.id))
    return client

@router.delete("/clients/{id}")
async def delete_client(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    await ClientService.delete_client(db, id)
    
    # Invalidate RAG Cache
    rag_cache.clear()

    await log_audit_trail(db, current_user.email, "DELETE", "clients", str(id))
    return {"status": "success"}

