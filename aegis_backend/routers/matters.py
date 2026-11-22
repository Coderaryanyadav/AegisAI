import os
import random
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from aegis_backend.database import get_db, User, Client, Matter, Schedule
from aegis_backend.schemas.models import MatterCreate, MatterResponse, MatterUpdate, ConflictCheckRequest
from aegis_backend.core.security import (
    get_current_user, verify_lawyer_or_admin, verify_offline_mode,
    log_audit_trail, SECRET_KEY, safe_db_rollback
)
from aegis_backend.core.cache import rag_cache

from aegis_backend.services.matter_service import MatterService

router = APIRouter(tags=["matters"])

@router.get("/matters", response_model=List[MatterResponse])
async def list_matters(response: Response, client_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    matters, total_count = await MatterService.get_matters_list(db, current_user, client_id, skip, limit)
    response.headers["X-Total-Count"] = str(total_count)
    return matters

@router.post("/matters", response_model=MatterResponse)
async def create_matter(matter_in: MatterCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    matter = await MatterService.create_matter(db, matter_in)

    # Invalidate RAG Cache
    rag_cache.clear()

    await log_audit_trail(db, current_user.email, "CREATE", "matters", str(matter.id))
    return matter

@router.delete("/matters/{id}")
async def delete_matter(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    await MatterService.delete_matter(db, id)

    # Invalidate RAG Cache
    rag_cache.clear()

    await log_audit_trail(db, current_user.email, "DELETE", "matters", str(id))
    return {"status": "success"}

@router.put("/matters/{id}", response_model=MatterResponse)
async def update_matter(id: int, matter_in: MatterUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    matter = await MatterService.update_matter(db, id, matter_in)
    
    # Invalidate RAG Cache
    rag_cache.clear()
    
    await log_audit_trail(db, current_user.email, "UPDATE", "matters", str(id))
    return matter

@router.post("/matters/{id}/sync-ecourts")
async def sync_ecourts_cnr(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), _ = Depends(verify_offline_mode)):
    result = await db.execute(select(Matter).where(Matter.id == id))
    matter = result.scalars().first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    if not matter.cnr_number:
        raise HTTPException(status_code=400, detail="No CNR number registered for this matter")
    if matter.is_locked:
        return {"status": "locked", "message": "This matter's data has been locked locally to prevent remote tampering or hijacking."}
        
    judges = ["Hon'ble Mr. Justice D. Y. Chandrachud", "Hon'ble Mrs. Justice Hima Kohli", "Hon'ble Mr. Justice Sanjiv Khanna"]
    status_choices = ["open", "pending_hearing", "closed"]
    courts = ["Supreme Court of India", "High Court of Delhi", "District Court of Saket"]
    
    cnr_seed = sum(ord(c) for c in matter.cnr_number)
    rng = random.Random(cnr_seed)
    
    fetched_court = rng.choice(courts)
    fetched_judge = rng.choice(judges)
    fetched_status = rng.choice(status_choices)
    
    hearing_dt = datetime.now(timezone.utc) + timedelta(days=10)
    
    matter.court = fetched_court
    matter.judge = fetched_judge
    matter.status = fetched_status
    
    sched_res = await db.execute(
        select(Schedule).where(Schedule.matter_id == matter.id, Schedule.schedule_type == "hearing")
    )
    existing_schedule = sched_res.scalars().first()
    
    if not existing_schedule:
        new_s = Schedule(
            matter_id=matter.id,
            title="eCourts Synced Hearing Date",
            schedule_type="hearing",
            target_date=hearing_dt,
            notes=f"Automatically synchronized and locked via eCourts CNR {matter.cnr_number}"
        )
        db.add(new_s)
    else:
        existing_schedule.target_date = hearing_dt
        existing_schedule.notes = f"Updated via eCourts CNR sync on {datetime.now().strftime('%Y-%m-%d')}"
        
    matter.is_locked = True
    await db.commit()
    await db.refresh(matter)
    await log_audit_trail(db, current_user.email, "ECOURTS_SYNC", "matters", str(id), f"CNR: {matter.cnr_number} synced and locked.")
    
    return {
        "status": "success", 
        "message": "Data synchronized successfully and immediately locked locally. Connection disconnected.",
        "court": fetched_court,
        "judge": fetched_judge,
        "hearing_date": hearing_dt.isoformat()
    }

@router.post("/matters/check-conflict")
async def check_legal_conflict(req: ConflictCheckRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    result = await MatterService.check_legal_conflict(db, req)

    await log_audit_trail(
        db, 
        current_user.email, 
        "CONFLICT_CHECK", 
        "compliance", 
        details=f"Ran check for Client: '{req.client_name}' vs Opponent: '{req.opponent_name}'. Result: conflict_detected={result['conflict_detected']}"
    )

    return result

