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
from aegis_backend.routers.clients import cleanup_matter_documents

router = APIRouter(tags=["matters"])



@router.get("/matters", response_model=List[MatterResponse])
async def list_matters(response: Response, client_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Matter)
    if current_user.role == "client":
        stmt_client = select(Client).filter(Client.email == current_user.email)
        res_client = await db.execute(stmt_client)
        client = res_client.scalars().first()
        if not client:
            response.headers["X-Total-Count"] = "0"
            return []
        stmt = stmt.filter(Matter.client_id == client.id)
    elif client_id:
        stmt = stmt.filter(Matter.client_id == client_id)
    
    # Calculate count
    if current_user.role == "client" and client:
        count_stmt = select(func.count(Matter.id)).filter(Matter.client_id == client.id)
    elif client_id:
        count_stmt = select(func.count(Matter.id)).filter(Matter.client_id == client_id)
    else:
        count_stmt = select(func.count(Matter.id))
        
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar()
    response.headers["X-Total-Count"] = str(total_count)

    res = await db.execute(stmt.offset(skip).limit(limit))
    matters = res.scalars().all()
    for m in matters:
        if m.is_locked and m.hmac_signature:
            payload = f"{m.id}:{m.case_number}:{m.court}:{m.judge}:{m.status}"
            expected_hmac = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(m.hmac_signature, expected_hmac):
                m.status = "TAMPERED_LOCK" # Warn user of DB tampering
    return matters

@router.post("/matters", response_model=MatterResponse)
async def create_matter(matter_in: MatterCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    matter = Matter(
        client_id=matter_in.client_id,
        case_number=matter_in.case_number,
        title=matter_in.title,
        court=matter_in.court,
        judge=matter_in.judge,
        opponent_name=matter_in.opponent_name,
        opposing_advocate=matter_in.opposing_advocate,
        status=matter_in.status,
        facts=matter_in.facts,
        cnr_number=matter_in.cnr_number
    )
    db.add(matter)
    await db.commit()
    await db.refresh(matter)

    # Invalidate RAG Cache
    rag_cache.clear()

    await log_audit_trail(db, current_user.email, "CREATE", "matters", str(matter.id))
    return matter

@router.delete("/matters/{id}")
async def delete_matter(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    stmt = select(Matter).filter(Matter.id == id)
    res = await db.execute(stmt)
    matter = res.scalars().first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    
    # Cascade clean documents, files, and vectors belonging to this matter
    await cleanup_matter_documents(matter.id, db)
    
    await db.delete(matter)
    await db.commit()

    # Invalidate RAG Cache
    rag_cache.clear()

    await log_audit_trail(db, current_user.email, "DELETE", "matters", str(id))
    return {"status": "success"}

@router.put("/matters/{id}", response_model=MatterResponse)
async def update_matter(id: int, matter_in: MatterUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    stmt = select(Matter).filter(Matter.id == id)
    res = await db.execute(stmt)
    matter = res.scalars().first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
        
    update_data = matter_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(matter, field, value)
        
    await db.commit()
    await db.refresh(matter)
    
    # Invalidate RAG Cache
    rag_cache.clear()
    
    await log_audit_trail(db, current_user.email, "UPDATE", "matters", str(id))
    return matter


@router.post("/matters/check-conflict")
async def check_legal_conflict(req: ConflictCheckRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    conflict_detected = False
    severity = "low"
    reasons = []

    clean_client = req.client_name.strip().upper()
    clean_opponent = req.opponent_name.strip().upper()

    if not clean_client or not clean_opponent:
        raise HTTPException(status_code=400, detail="Client name and Opponent name are required.")

    from sqlalchemy import or_
    
    clean_client_wildcard = f"%{clean_client}%"
    clean_opponent_wildcard = f"%{clean_opponent}%"
    
    # 1. Check if the opponent matches any active client names (DIRECT CONFLICT)
    stmt_clients = select(Client).filter(
        or_(
            Client.name.ilike(clean_opponent_wildcard),
            func.upper(clean_opponent).like(func.concat('%', func.upper(Client.name), '%'))
        )
    )
    res_clients = await db.execute(stmt_clients)
    clients = res_clients.scalars().all()
    for c in clients:
        conflict_detected = True
        severity = "high"
        reasons.append(f"DIRECT CONFLICT: Opponent '{req.opponent_name}' matches active client folder '{c.name}' (Client ID: {c.id}).")

    # 2. Check matters
    stmt_matters = select(Matter).options(selectinload(Matter.client)).filter(
        or_(
            Matter.opponent_name.ilike(clean_client_wildcard),
            func.upper(clean_client).like(func.concat('%', func.upper(Matter.opponent_name), '%')),
            Matter.client.has(Client.name.ilike(clean_opponent_wildcard)),
            Matter.client.has(func.upper(clean_opponent).like(func.concat('%', func.upper(Client.name), '%')))
        )
    )
    res_matters = await db.execute(stmt_matters)
    matters = res_matters.scalars().all()
    
    for m in matters:
        if m.opponent_name:
            clean_matter_opp = m.opponent_name.strip().upper()
            if clean_client in clean_matter_opp or clean_matter_opp in clean_client:
                conflict_detected = True
                severity = "high"
                reasons.append(f"INDIRECT CONFLICT: Prospective client '{req.client_name}' is listed as Opponent in active matter file '{m.title}' (Matter ID: {m.id}, Client: {m.client.name if m.client else 'Unknown'}).")
        
        if m.client:
            clean_matter_client = m.client.name.strip().upper()
            if clean_opponent in clean_matter_client or clean_matter_client in clean_opponent:
                conflict_detected = True
                if severity != "high":
                    severity = "medium"
                reasons.append(f"ASSOCIATED RISK: Prospective opponent '{req.opponent_name}' matches client '{m.client.name}' in matter file '{m.title}'.")

    await log_audit_trail(
        db, 
        current_user.email, 
        "CONFLICT_CHECK", 
        "compliance", 
        details=f"Ran check for Client: '{req.client_name}' vs Opponent: '{req.opponent_name}'. Result: conflict_detected={conflict_detected}"
    )

    return {
        "client_name": req.client_name,
        "opponent_name": req.opponent_name,
        "conflict_detected": conflict_detected,
        "severity": severity,
        "reasons": reasons
    }

