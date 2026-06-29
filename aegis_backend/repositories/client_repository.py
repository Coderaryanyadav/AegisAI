from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from aegis_backend.database import Client, Matter, Document

class ClientRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, client_id: int) -> Optional[Client]:
        stmt = select(Client).filter(Client.id == client_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_clients(self, skip: int = 0, limit: int = 100) -> Tuple[List[Client], int]:
        count_stmt = select(func.count(Client.id))
        stmt = select(Client)
        
        count_res = await self.db.execute(count_stmt)
        total_count = count_res.scalar() or 0
        
        res = await self.db.execute(stmt.offset(skip).limit(limit))
        return list(res.scalars().all()), total_count

    async def list_clients_for_email(self, email: str, skip: int = 0, limit: int = 100) -> Tuple[List[Client], int]:
        count_stmt = select(func.count(Client.id)).filter(Client.email == email)
        stmt = select(Client).filter(Client.email == email)
        
        count_res = await self.db.execute(count_stmt)
        total_count = count_res.scalar() or 0
        
        res = await self.db.execute(stmt.offset(skip).limit(limit))
        return list(res.scalars().all()), total_count

    async def create(self, client: Client) -> Client:
        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)
        return client

    async def get_matters_for_client(self, client_id: int) -> List[Matter]:
        stmt = select(Matter).filter(Matter.client_id == client_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_documents_for_matter(self, matter_id: int) -> List[Document]:
        stmt = select(Document).filter(Document.matter_id == matter_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_document(self, doc: Document):
        await self.db.delete(doc)

    async def delete_client(self, client: Client):
        await self.db.delete(client)
        await self.db.commit()
