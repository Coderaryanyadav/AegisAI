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

@router.post("/matters/{id}/sync-ecourts")
async def sync_ecourts_cnr(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    stmt = select(Matter).filter(Matter.id == id)
    res = await db.execute(stmt)
    matter = res.scalars().first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    if not matter.cnr_number:
        raise HTTPException(status_code=400, detail="No CNR number registered for this matter")
    if matter.is_locked:
        return {"status": "locked", "message": "This matter's data has been locked locally to prevent remote tampering or hijacking. (eCourts Sync Simulation Mode)", "is_simulation": True}
    
    # In simulation mode, we bypass external DNS checks to prevent metadata leakage.
    is_online = True

    if not is_online:
        raise HTTPException(
            status_code=503,
            detail="Offline mode active. Internet connection required to sync with the eCourts platform. Please go online and try again."
        )
    from aegis_backend.services.matter_service import MatterService
    result = await MatterService.sync_ecourts_cnr(db, matter)
    await log_audit_trail(db, current_user.email, "ECOURTS_SYNC", "matters", str(id), f"CNR: {matter.cnr_number} synced and locked.")
    return result

@router.get("/ecourts/lookup")
async def ecourts_lookup(cnr: str, current_user: User = Depends(verify_lawyer_or_admin), db: AsyncSession = Depends(get_db)):
    if not cnr or len(cnr.strip()) < 6:
        raise HTTPException(status_code=400, detail="A valid CNR number is required (min 6 characters)")

    cnr = cnr.strip().upper()

    # In simulation mode, we bypass external DNS checks to prevent metadata leakage.
    is_online = True

    if not is_online:
        raise HTTPException(
            status_code=503,
            detail="No internet connection detected. Cannot reach eCourts platform. Please check your network."
        )

    judges = [
        "Hon'ble Mr. Justice D. Y. Chandrachud",
        "Hon'ble Mrs. Justice Hima Kohli",
        "Hon'ble Mr. Justice Sanjiv Khanna",
        "Hon'ble Mr. Justice B. R. Gavai",
        "Hon'ble Ms. Justice Indira Banerjee"
    ]
    status_choices = ["Open", "Pending Hearing", "Reserved for Judgment", "Disposed"]
    courts = [
        "Supreme Court of India",
        "High Court of Bombay",
        "High Court of Delhi",
        "District Court of Saket, New Delhi",
        "City Civil Court, Mumbai",
        "High Court of Madras"
    ]
    case_types = ["Civil Suit", "Criminal Appeal", "Writ Petition", "Special Leave Petition", "Company Matter"]
    petitioners = ["State of Maharashtra", "Union of India", "Petitioner Corp Pvt. Ltd.", "M/s Bharat Enterprises"]
    respondents = ["Respondent Industries Ltd.", "State Bank of India", "Income Tax Department"]

    cnr_seed = sum(ord(c) for c in cnr)
    rng = random.Random(cnr_seed)

    fetched_court = rng.choice(courts)
    fetched_judge = rng.choice(judges)
    fetched_status = rng.choice(status_choices)
    fetched_case_type = rng.choice(case_types)
    fetched_petitioner = rng.choice(petitioners)
    fetched_respondent = rng.choice(respondents)
    fetched_case_number = f"CS No. {rng.randint(100, 9999)}/{datetime.now().year - rng.randint(0, 5)}"
    next_date = (datetime.now() + timedelta(days=rng.randint(5, 60))).strftime("%d %B %Y")
    filed_date = (datetime.now() - timedelta(days=rng.randint(30, 1800))).strftime("%d %B %Y")

    await log_audit_trail(db, current_user.email, "ECOURTS_LOOKUP", "ecourts", cnr, f"Online lookup for CNR {cnr}")

    return {
        "cnr": cnr,
        "case_title": f"{fetched_petitioner} vs. {fetched_respondent}",
        "case_number": fetched_case_number,
        "case_type": fetched_case_type,
        "court": fetched_court,
        "judge": fetched_judge,
        "status": fetched_status,
        "next_date": next_date,
        "filing_date": filed_date,
        "is_simulation": True,
        "raw_text": (
            f"Case No: {fetched_case_number} | CNR: {cnr} (SIMULATION)\n"
            f"Before: {fetched_judge}\n"
            f"Court: {fetched_court}\n"
            f"Parties: {fetched_petitioner} vs. {fetched_respondent}\n"
            f"Type: {fetched_case_type} | Status: {fetched_status}\n"
            f"Filed: {filed_date} | Next Hearing: {next_date}"
        )
    }

@router.post("/matters/check-conflict")
async def check_legal_conflict(req: ConflictCheckRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    conflict_detected = False
    severity = "low"
    reasons = []

    clean_client = req.client_name.strip().upper()
    clean_opponent = req.opponent_name.strip().upper()

    if not clean_client or not clean_opponent:
        raise HTTPException(status_code=400, detail="Client name and Opponent name are required.")

    stmt_clients = select(Client)
    res_clients = await db.execute(stmt_clients)
    clients = res_clients.scalars().all()
    for c in clients:
        if clean_opponent in c.name.upper() or c.name.upper() in clean_opponent:
            conflict_detected = True
            severity = "high"
            reasons.append(f"DIRECT CONFLICT: Opponent '{req.opponent_name}' matches active client folder '{c.name}' (Client ID: {c.id}).")

    stmt_matters = select(Matter).options(selectinload(Matter.client))
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

