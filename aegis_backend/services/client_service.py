import os
import logging
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from aegis_backend.database import Client, User
from aegis_backend.repositories.client_repository import ClientRepository
from aegis_backend.schemas.models import ClientCreate
from aegis_backend.vector_store import vector_store

logger = logging.getLogger("aegis_ai.backend")

class ClientService:
    @staticmethod
    async def get_clients_list(
        db: AsyncSession,
        current_user: User,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Client], int]:
        repo = ClientRepository(db)
        if current_user.role == "client":
            return await repo.list_clients_for_email(email=current_user.email, skip=skip, limit=limit)
        return await repo.list_clients(skip=skip, limit=limit)

    @staticmethod
    async def create_client(db: AsyncSession, client_in: ClientCreate) -> Client:
        repo = ClientRepository(db)
        client = Client(
            name=client_in.name,
            email=client_in.email,
            phone=client_in.phone,
            notes=client_in.notes
        )
        return await repo.create(client)

    @staticmethod
    async def cleanup_matter_documents(db: AsyncSession, matter_id: int):
        repo = ClientRepository(db)
        docs = await repo.get_documents_for_matter(matter_id)
        for doc in docs:
            try:
                vector_store.delete_document_vectors(doc.id)
            except Exception as e:
                logger.warning(f"Error removing vectors for doc {doc.id} during matter deletion: {e}")
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
            if os.path.exists(doc.file_path + ".txt"):
                os.remove(doc.file_path + ".txt")
            await repo.delete_document(doc)

    @staticmethod
    async def delete_client(db: AsyncSession, client_id: int):
        repo = ClientRepository(db)
        client = await repo.get_by_id(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Cascade clean documents, files, and vectors of all matters belonging to this client
        matters = await repo.get_matters_for_client(client_id)
        for matter in matters:
            await ClientService.cleanup_matter_documents(db, matter.id)

        await repo.delete_client(client)
