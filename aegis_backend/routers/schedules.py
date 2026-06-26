from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from aegis_backend.database import get_db, User, Client, Matter, Schedule
from aegis_backend.schemas.models import ScheduleCreate, ScheduleResponse
from aegis_backend.core.security import get_current_user, verify_lawyer_or_admin, log_audit_trail

router = APIRouter(tags=["schedules"])

@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(response: Response, matter_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Schedule)
    if current_user.role == "client":
        stmt_client = select(Client).filter(Client.email == current_user.email)
        res_client = await db.execute(stmt_client)
        client = res_client.scalars().first()
        if not client:
            response.headers["X-Total-Count"] = "0"
            return []
        
        stmt_matters = select(Matter.id).filter(Matter.client_id == client.id)
        res_matters = await db.execute(stmt_matters)
        mat_ids = res_matters.scalars().all()
        
        if matter_id and matter_id in mat_ids:
            stmt = stmt.filter(Schedule.matter_id == matter_id)
        else:
            stmt = stmt.filter(Schedule.matter_id.in_(mat_ids))
    elif matter_id:
        stmt = stmt.filter(Schedule.matter_id == matter_id)
    
    count_stmt = select(func.count(Schedule.id)).select_from(stmt.subquery())
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar()
    response.headers["X-Total-Count"] = str(total_count)
    
    res = await db.execute(stmt.order_by(Schedule.target_date.asc()).offset(skip).limit(limit))
    return res.scalars().all()

@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(schedule_in: ScheduleCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    sch = Schedule(
        matter_id=schedule_in.matter_id,
        title=schedule_in.title,
        schedule_type=schedule_in.schedule_type,
        target_date=schedule_in.target_date,
        notes=schedule_in.notes
    )
    db.add(sch)
    await db.commit()
    await db.refresh(sch)
    await log_audit_trail(db, current_user.email, "CREATE", "schedules", str(sch.id))
    return sch

@router.put("/schedules/{id}/complete", response_model=ScheduleResponse)
async def complete_schedule(id: int, completed: bool = True, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    stmt = select(Schedule).filter(Schedule.id == id)
    res = await db.execute(stmt)
    sch = res.scalars().first()
    if not sch:
        raise HTTPException(status_code=404, detail="Schedule event not found")
    sch.is_completed = completed
    await db.commit()
    return sch

