import os
import random
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from aegis_backend.database import get_db, User, Client, Matter, Schedule
from aegis_backend.schemas.models import MatterCreate, MatterResponse, ConflictCheckRequest
from aegis_backend.core.security import (
    get_current_user, verify_lawyer_or_admin, verify_offline_mode,
    log_audit_trail, SECRET_KEY
)
from aegis_backend.routers.clients import cleanup_matter_documents

router = APIRouter(prefix="/api", tags=["matters"])

def _safe_db_rollback(db_candidate=None):
    try:
        db = db_candidate
        if db is None:
            return
        if hasattr(db, "rollback"):
            db.rollback()
    except Exception:
        pass

@router.get("/matters", response_model=List[MatterResponse])
def list_matters(client_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Matter)
    if current_user.role == "client":
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if not client:
            return []
        query = query.filter(Matter.client_id == client.id)
    elif client_id:
        query = query.filter(Matter.client_id == client_id)
    matters = query.offset(skip).limit(limit).all()
    for m in matters:
        if m.is_locked and m.hmac_signature:
            payload = f"{m.id}:{m.case_number}:{m.court}:{m.judge}:{m.status}"
            expected_hmac = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(m.hmac_signature, expected_hmac):
                m.status = "TAMPERED_LOCK" # Warn user of DB tampering
    return matters

@router.post("/matters", response_model=MatterResponse)
def create_matter(matter_in: MatterCreate, db: Session = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
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
    db.commit()
    db.refresh(matter)
    log_audit_trail(db, current_user.email, "CREATE", "matters", str(matter.id))
    return matter

@router.delete("/matters/{id}")
def delete_matter(id: int, db: Session = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    matter = db.query(Matter).filter(Matter.id == id).first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    
    # Cascade clean documents, files, and vectors belonging to this matter
    cleanup_matter_documents(matter.id, db)
    
    db.delete(matter)
    db.commit()
    log_audit_trail(db, current_user.email, "DELETE", "matters", str(id))
    return {"status": "success"}

@router.post("/matters/{id}/sync-ecourts")
async def sync_ecourts_cnr(id: int, db: Session = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    matter = db.query(Matter).filter(Matter.id == id).first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    if not matter.cnr_number:
        raise HTTPException(status_code=400, detail="No CNR number registered for this matter")
    if matter.is_locked:
        return {"status": "locked", "message": "This matter's data has been locked locally to prevent remote tampering or hijacking. (eCourts Sync Simulation Mode)", "is_simulation": True}
    
    # Check actual internet connectivity (async)
    import httpx
    is_online = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get("https://www.google.com")
            if res.status_code == 200:
                is_online = True
    except Exception:
        _safe_db_rollback(db)
        pass

    if not is_online:
        raise HTTPException(
            status_code=503,
            detail="Offline mode active. Internet connection required to sync with the eCourts platform. Please go online and try again."
        )

    # Call online latency test target to simulate actual remote API request delay
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get("https://httpbin.org/delay/1")
    except Exception as e:
        _safe_db_rollback(db)
    
    judges = ["Hon'ble Mr. Justice D. Y. Chandrachud", "Hon'ble Mrs. Justice Hima Kohli", "Hon'ble Mr. Justice Sanjiv Khanna"]
    status_choices = ["open", "pending_hearing", "closed"]
    courts = ["Supreme Court of India", "High Court of Delhi", "District Court of Saket"]
    
    cnr_seed = sum(ord(c) for c in matter.cnr_number)
    random.seed(cnr_seed)
    
    fetched_court = random.choice(courts)
    fetched_judge = random.choice(judges)
    fetched_status = random.choice(status_choices)
    
    hearing_date = (datetime.now() + timedelta(days=10)).isoformat()
    
    matter.court = fetched_court
    matter.judge = fetched_judge
    matter.status = fetched_status
    
    existing_schedule = db.query(Schedule).filter(
        Schedule.matter_id == matter.id, 
        Schedule.schedule_type == "hearing"
    ).first()
    
    if not existing_schedule:
        new_s = Schedule(
            matter_id=matter.id,
            title="eCourts Synced Hearing Date",
            schedule_type="hearing",
            target_date=hearing_date,
            notes=f"Automatically synchronized and locked via eCourts CNR {matter.cnr_number}"
        )
        db.add(new_s)
    else:
        existing_schedule.target_date = hearing_date
        existing_schedule.notes = f"Updated via eCourts CNR sync on {datetime.now().strftime('%Y-%m-%d')}"
        
    matter.is_locked = True
    
    payload = f"{matter.id}:{matter.case_number}:{matter.court}:{matter.judge}:{matter.status}"
    matter.hmac_signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    
    db.commit()
    db.refresh(matter)
    log_audit_trail(db, current_user.email, "ECOURTS_SYNC", "matters", str(id), f"CNR: {matter.cnr_number} synced and locked.")
    
    return {
        "status": "success", 
        "message": "Data synchronized successfully and immediately locked locally. Connection disconnected. (eCourts Sync Simulation Mode)",
        "is_simulation": True,
        "court": fetched_court,
        "judge": fetched_judge,
        "hearing_date": hearing_date
    }

@router.get("/ecourts/lookup")
async def ecourts_lookup(cnr: str, current_user: User = Depends(verify_lawyer_or_admin), db: Session = Depends(get_db)):
    if not cnr or len(cnr.strip()) < 6:
        raise HTTPException(status_code=400, detail="A valid CNR number is required (min 6 characters)")

    cnr = cnr.strip().upper()

    import httpx
    is_online = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get("https://www.google.com")
            if res.status_code == 200:
                is_online = True
    except Exception:
        _safe_db_rollback(db)
        pass

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
    random.seed(cnr_seed)

    fetched_court = random.choice(courts)
    fetched_judge = random.choice(judges)
    fetched_status = random.choice(status_choices)
    fetched_case_type = random.choice(case_types)
    fetched_petitioner = random.choice(petitioners)
    fetched_respondent = random.choice(respondents)
    fetched_case_number = f"CS No. {random.randint(100, 9999)}/{datetime.now().year - random.randint(0, 5)}"
    next_date = (datetime.now() + timedelta(days=random.randint(5, 60))).strftime("%d %B %Y")
    filed_date = (datetime.now() - timedelta(days=random.randint(30, 1800))).strftime("%d %B %Y")

    log_audit_trail(db, current_user.email, "ECOURTS_LOOKUP", "ecourts", cnr, f"Online lookup for CNR {cnr}")

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
def check_legal_conflict(req: ConflictCheckRequest, db: Session = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    conflict_detected = False
    severity = "low"
    reasons = []

    clean_client = req.client_name.strip().upper()
    clean_opponent = req.opponent_name.strip().upper()

    if not clean_client or not clean_opponent:
        raise HTTPException(status_code=400, detail="Client name and Opponent name are required.")

    clients = db.query(Client).all()
    for c in clients:
        if clean_opponent in c.name.upper() or c.name.upper() in clean_opponent:
            conflict_detected = True
            severity = "high"
            reasons.append(f"DIRECT CONFLICT: Opponent '{req.opponent_name}' matches active client folder '{c.name}' (Client ID: {c.id}).")

    matters = db.query(Matter).all()
    for m in matters:
        if m.opponent_name:
            clean_matter_opp = m.opponent_name.strip().upper()
            if clean_client in clean_matter_opp or clean_matter_opp in clean_client:
                conflict_detected = True
                severity = "high"
                reasons.append(f"INDIRECT CONFLICT: Prospective client '{req.client_name}' is listed as Opponent in active matter file '{m.title}' (Matter ID: {m.id}, Client: {m.client.name}).")
        
        if m.client:
            clean_matter_client = m.client.name.strip().upper()
            if clean_opponent in clean_matter_client or clean_matter_client in clean_opponent:
                conflict_detected = True
                if severity != "high":
                    severity = "medium"
                reasons.append(f"ASSOCIATED RISK: Prospective opponent '{req.opponent_name}' matches client '{m.client.name}' in matter file '{m.title}'.")

    log_audit_trail(
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
