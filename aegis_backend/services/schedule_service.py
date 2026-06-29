from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from aegis_backend.database import Schedule, User
from aegis_backend.repositories.schedule_repository import ScheduleRepository
from aegis_backend.core.security import log_audit_trail

class ScheduleService:
    @staticmethod
    async def get_schedule(db: AsyncSession, schedule_id: int) -> Optional[Schedule]:
        repo = ScheduleRepository(db)
        return await repo.get_by_id(schedule_id)

    @staticmethod
    async def get_schedules_list(
        db: AsyncSession,
        current_user: User,
        matter_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Schedule], int]:
        repo = ScheduleRepository(db)
        if current_user.role == "client":
            return await repo.list_schedules_for_client(
                client_email=current_user.email,
                matter_id=matter_id,
                skip=skip,
                limit=limit
            )
        return await repo.list_schedules(
            matter_id=matter_id,
            skip=skip,
            limit=limit
        )

    @staticmethod
    async def create_new_schedule(
        db: AsyncSession,
        current_user: User,
        matter_id: int,
        title: str,
        schedule_type: str,
        target_date: str,
        notes: Optional[str] = None
    ) -> Schedule:
        repo = ScheduleRepository(db)
        sch = await repo.create(
            matter_id=matter_id,
            title=title,
            schedule_type=schedule_type,
            target_date=target_date,
            notes=notes
        )
        await log_audit_trail(db, current_user.email, "CREATE", "schedules", str(sch.id))
        return sch

    @staticmethod
    async def toggle_completion(
        db: AsyncSession,
        schedule_id: int,
        completed: bool = True
    ) -> Optional[Schedule]:
        repo = ScheduleRepository(db)
        sch = await repo.get_by_id(schedule_id)
        if not sch:
            return None
        sch.is_completed = completed
        return await repo.save(sch)
