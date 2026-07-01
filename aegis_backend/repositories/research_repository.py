from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from aegis_backend.database import Document, Matter, Schedule, BareActSection, Client

class ResearchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_document_by_id(self, doc_id: int) -> Optional[Document]:
        stmt = select(Document).filter(Document.id == doc_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_bare_act_section(self, act: str, section: str) -> Optional[BareActSection]:
        stmt = select(BareActSection).filter(
            BareActSection.act == act,
            BareActSection.section == section
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_all_matters(self) -> List[Matter]:
        stmt = select(Matter)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_matter_by_id(self, matter_id: int) -> Optional[Matter]:
        stmt = select(Matter).filter(Matter.id == matter_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_client_by_id(self, client_id: int) -> Optional[Client]:
        stmt = select(Client).filter(Client.id == client_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_schedule_by_id(self, schedule_id: int) -> Optional[Schedule]:
        stmt = select(Schedule).filter(Schedule.id == schedule_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def check_schedule_exists(self, matter_id: int, title: str, target_date: str) -> Optional[Schedule]:
        stmt = select(Schedule).filter(
            Schedule.matter_id == matter_id,
            Schedule.title == title,
            Schedule.target_date == target_date
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def create_schedule(self, schedule: Schedule) -> Schedule:
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule
