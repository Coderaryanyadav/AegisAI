from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_backend.database import get_db, User
from aegis_backend.schemas.models import ScheduleCreate, ScheduleResponse
from aegis_backend.core.security import get_current_user, verify_lawyer_or_admin
from aegis_backend.services.schedule_service import ScheduleService

router = APIRouter(tags=["schedules"])

@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(
    response: Response,
    matter_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    schedules, total_count = await ScheduleService.get_schedules_list(
        db=db,
        current_user=current_user,
        matter_id=matter_id,
        skip=skip,
        limit=limit
    )
    response.headers["X-Total-Count"] = str(total_count)
    return schedules

@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    schedule_in: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_lawyer_or_admin)
):
    return await ScheduleService.create_new_schedule(
        db=db,
        current_user=current_user,
        matter_id=schedule_in.matter_id,
        title=schedule_in.title,
        schedule_type=schedule_in.schedule_type,
        target_date=schedule_in.target_date,
        notes=schedule_in.notes
    )

@router.put("/schedules/{id}/complete", response_model=ScheduleResponse)
async def complete_schedule(
    id: int,
    completed: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_lawyer_or_admin)
):
    sch = await ScheduleService.toggle_completion(db=db, schedule_id=id, completed=completed)
    if not sch:
        raise HTTPException(status_code=404, detail="Schedule event not found")
    return sch

