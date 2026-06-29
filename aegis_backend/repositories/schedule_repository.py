from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from aegis_backend.database import Schedule, Client, Matter

class ScheduleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, schedule_id: int) -> Optional[Schedule]:
        stmt = select(Schedule).filter(Schedule.id == schedule_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_schedules_for_client(
        self, client_email: str, matter_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Schedule], int]:
        stmt_client = select(Client).filter(Client.email == client_email)
        res_client = await self.db.execute(stmt_client)
        client = res_client.scalars().first()
        if not client:
            return [], 0

        stmt_matters = select(Matter.id).filter(Matter.client_id == client.id)
        res_matters = await self.db.execute(stmt_matters)
        mat_ids = res_matters.scalars().all()

        stmt = select(Schedule)
        if matter_id and matter_id in mat_ids:
            stmt = stmt.filter(Schedule.matter_id == matter_id)
        else:
            stmt = stmt.filter(Schedule.matter_id.in_(mat_ids))

        count_stmt = select(func.count(Schedule.id)).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total_count = count_res.scalar() or 0

        res = await self.db.execute(
            stmt.order_by(Schedule.target_date.asc()).offset(skip).limit(limit)
        )
        return list(res.scalars().all()), total_count

    async def list_schedules(
        self, matter_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Schedule], int]:
        stmt = select(Schedule)
        if matter_id:
            stmt = stmt.filter(Schedule.matter_id == matter_id)

        count_stmt = select(func.count(Schedule.id)).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total_count = count_res.scalar() or 0

        res = await self.db.execute(
            stmt.order_by(Schedule.target_date.asc()).offset(skip).limit(limit)
        )
        return list(res.scalars().all()), total_count

    async def create(self, matter_id: int, title: str, schedule_type: str, target_date: str, notes: Optional[str] = None) -> Schedule:
        sch = Schedule(
            matter_id=matter_id,
            title=title,
            schedule_type=schedule_type,
            target_date=target_date,
            notes=notes
        )
        self.db.add(sch)
        await self.db.commit()
        await self.db.refresh(sch)
        return sch

    async def save(self, schedule: Schedule) -> Schedule:
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule
