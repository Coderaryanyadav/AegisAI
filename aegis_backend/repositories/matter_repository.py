from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from aegis_backend.database import Matter, Client

class MatterRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, matter_id: int) -> Optional[Matter]:
        stmt = select(Matter).filter(Matter.id == matter_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_client_by_email(self, email: str) -> Optional[Client]:
        stmt = select(Client).filter(Client.email == email)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_matters(
        self, client_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Matter], int]:
        stmt = select(Matter)
        count_stmt = select(func.count(Matter.id))

        if client_id:
            stmt = stmt.filter(Matter.client_id == client_id)
            count_stmt = count_stmt.filter(Matter.client_id == client_id)

        count_res = await self.db.execute(count_stmt)
        total_count = count_res.scalar() or 0

        res = await self.db.execute(stmt.offset(skip).limit(limit))
        return list(res.scalars().all()), total_count

    async def create(self, matter: Matter) -> Matter:
        self.db.add(matter)
        await self.db.commit()
        await self.db.refresh(matter)
        return matter

    async def update(self, matter: Matter) -> Matter:
        await self.db.commit()
        await self.db.refresh(matter)
        return matter

    async def delete(self, matter: Matter):
        await self.db.delete(matter)
        await self.db.commit()

    async def check_direct_conflict(self, clean_opponent: str) -> List[Client]:
        clean_opponent_wildcard = f"%{clean_opponent}%"
        stmt = select(Client).filter(
            or_(
                Client.name.ilike(clean_opponent_wildcard),
                func.upper(clean_opponent).like(func.concat('%', func.upper(Client.name), '%'))
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def check_indirect_conflict(self, clean_client: str, clean_opponent: str) -> List[Matter]:
        clean_client_wildcard = f"%{clean_client}%"
        clean_opponent_wildcard = f"%{clean_opponent}%"
        
        stmt = select(Matter).options(selectinload(Matter.client)).filter(
            or_(
                Matter.opponent_name.ilike(clean_client_wildcard),
                func.upper(clean_client).like(func.concat('%', func.upper(Matter.opponent_name), '%')),
                Matter.client.has(Client.name.ilike(clean_opponent_wildcard)),
                Matter.client.has(func.upper(clean_opponent).like(func.concat('%', func.upper(Client.name), '%')))
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
