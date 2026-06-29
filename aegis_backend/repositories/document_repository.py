from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from aegis_backend.database import Document, Client, Matter

class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, doc_id: int) -> Optional[Document]:
        stmt = select(Document).filter(Document.id == doc_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_by_hash(self, file_hash: str) -> Optional[Document]:
        stmt = select(Document).filter(Document.file_hash == file_hash)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_documents_for_client(
        self, client_email: str, matter_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Document], int]:
        stmt_client = select(Client).filter(Client.email == client_email)
        res_client = await self.db.execute(stmt_client)
        client = res_client.scalars().first()
        if not client:
            return [], 0

        stmt_matters = select(Matter.id).filter(Matter.client_id == client.id)
        res_matters = await self.db.execute(stmt_matters)
        mat_ids = res_matters.scalars().all()

        stmt = select(Document)
        if matter_id and matter_id in mat_ids:
            stmt = stmt.filter(Document.matter_id == matter_id)
        else:
            stmt = stmt.filter(Document.matter_id.in_(mat_ids))

        count_stmt = select(func.count(Document.id)).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total_count = count_res.scalar() or 0

        res = await self.db.execute(stmt.offset(skip).limit(limit))
        return list(res.scalars().all()), total_count

    async def list_documents(
        self, matter_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Document], int]:
        stmt = select(Document)
        if matter_id:
            stmt = stmt.filter(Document.matter_id == matter_id)

        count_stmt = select(func.count(Document.id)).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total_count = count_res.scalar() or 0

        res = await self.db.execute(stmt.offset(skip).limit(limit))
        return list(res.scalars().all()), total_count

    async def create(self, doc: Document) -> Document:
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def delete(self, doc: Document):
        await self.db.delete(doc)
        await self.db.commit()
