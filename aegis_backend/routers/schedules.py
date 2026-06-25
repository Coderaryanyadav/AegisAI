from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from aegis_backend.database import get_db, User, Client, Matter, Schedule
from aegis_backend.schemas.models import ScheduleCreate, ScheduleResponse
from aegis_backend.core.security import get_current_user, verify_lawyer_or_admin, log_audit_trail

router = APIRouter(prefix="/api", tags=["schedules"])

@router.get("/schedules", response_model=List[ScheduleResponse])
def list_schedules(matter_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Schedule)
    if current_user.role == "client":
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if not client:
            return []
        mat_ids = [m.id for m in db.query(Matter).filter(Matter.client_id == client.id).all()]
        if matter_id and matter_id in mat_ids:
            query = query.filter(Schedule.matter_id == matter_id)
        else:
            query = query.filter(Schedule.matter_id.in_(mat_ids))
    elif matter_id:
        query = query.filter(Schedule.matter_id == matter_id)
    return query.order_by(Schedule.target_date.asc()).offset(skip).limit(limit).all()

@router.post("/schedules", response_model=ScheduleResponse)
def create_schedule(schedule_in: ScheduleCreate, db: Session = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    sch = Schedule(
        matter_id=schedule_in.matter_id,
        title=schedule_in.title,
        schedule_type=schedule_in.schedule_type,
        target_date=schedule_in.target_date,
        notes=schedule_in.notes
    )
    db.add(sch)
    db.commit()
    db.refresh(sch)
    log_audit_trail(db, current_user.email, "CREATE", "schedules", str(sch.id))
    return sch

@router.put("/schedules/{id}/complete", response_model=ScheduleResponse)
def complete_schedule(id: int, completed: bool = True, db: Session = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    sch = db.query(Schedule).filter(Schedule.id == id).first()
    if not sch:
        raise HTTPException(status_code=404, detail="Schedule event not found")
    sch.is_completed = completed
    db.commit()
    return sch
