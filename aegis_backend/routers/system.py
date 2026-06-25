import os
import sys
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from aegis_backend.database import get_db, User, Document, Matter, Client, AuditLog, AEGIS_DIR, DB_PATH
from aegis_backend.core import security
from aegis_backend.core.security import get_current_user, verify_admin
from aegis_backend.ollama_service import OllamaService

router = APIRouter(prefix="/api", tags=["system"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connectivity check failed: {str(e)}"
        )

@router.get("/system/connection-mode")
def get_connection_mode(current_user: User = Depends(get_current_user)):
    return {"online": security.SYSTEM_ONLINE_MODE}

@router.post("/system/connection-mode")
def set_connection_mode(req: Dict[str, bool], current_user: User = Depends(verify_admin)):
    security.SYSTEM_ONLINE_MODE = req.get("online", False)
    return {"online": security.SYSTEM_ONLINE_MODE}

@router.get("/system/privacy-policy")
def get_privacy_policy():
    return {
        "privacy_policy": (
            "AegisAI operates 100% offline. No case files, search history, document uploads, "
            "or user metadata are ever transmitted to external servers. All data is processed "
            "locally on your device and encrypted at rest in accordance with the IT Act 2000 "
            "and Digital Personal Data Protection Act (DPDPA) 2023."
        )
    }

@router.get("/system/ai-disclaimer")
def get_ai_disclaimer():
    return {
        "disclaimer": (
            "AI-generated content, document analysis, risk scanning, and timeline extractions "
            "are provided for informational and defense assistance purposes only. They do not "
            "constitute professional legal advice and must be independently verified by a qualified "
            "advocate."
        )
    }

@router.get("/system/audit-logs")
def get_compliance_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(verify_admin)):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

@router.get("/system/audit-logs/export")
def export_signed_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(verify_admin)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    
    report_lines = []
    report_lines.append("================================================================================")
    report_lines.append("                       AEGIS LEGAL AI COMPLIANCE AUDIT REPORT                   ")
    report_lines.append("================================================================================")
    report_lines.append(f"Exported At: {datetime.now(timezone.utc).isoformat()} UTC")
    report_lines.append(f"Exported By: {current_user.email}")
    report_lines.append(f"System Directory: {AEGIS_DIR}")
    report_lines.append("--------------------------------------------------------------------------------")
    report_lines.append(f"{'TIMESTAMP (UTC)':<20} | {'USER EMAIL':<30} | {'ACTION':<15} | {'TARGET':<10} | DETAILS")
    report_lines.append("--------------------------------------------------------------------------------")
    
    for l in logs:
        ts = l.timestamp.isoformat() if l.timestamp else "N/A"
        email = l.user_email or "N/A"
        act = l.action or "N/A"
        tgt = l.target_type or "N/A"
        det = l.details or ""
        report_lines.append(f"{ts:<20} | {email:<30} | {act:<15} | {tgt:<10} | {det}")
        
    report_lines.append("================================================================================")
    report_lines.append("                       END OF AEGIS AUDIT TRAIL LOG                            ")
    report_lines.append("================================================================================")
    
    report_content = "\n".join(report_lines)
    
    key_path = os.path.join(AEGIS_DIR, ".master.key")
    try:
        with open(key_path, "rb") as f:
            master_key = f.read()
    except Exception:
        master_key = b"fallback-aegis-key-hash"
        
    signature = hmac.new(master_key, report_content.encode("utf-8"), hashlib.sha256).hexdigest()
    signed_document = f"{report_content}\n\n[CRYPTOGRAPHIC INTEGRITY SIGNATURE]\nHMAC-SHA256: {signature}\n"
    
    return Response(
        content=signed_document,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=aegis_compliance_audit_report.txt"
        }
    )

@router.get("/system/models")
async def list_ollama_models(current_user: User = Depends(get_current_user)):
    models = await OllamaService.get_available_models()
    return {"models": models}

@router.get("/system/status")
async def system_diagnostics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    models = await OllamaService.get_available_models()
    ollama_running = len(models) > 0

    doc_count = db.query(Document).count()
    matter_count = db.query(Matter).count()
    client_count = db.query(Client).count()

    db_size = 0
    if os.path.exists(DB_PATH):
        db_size = os.path.getsize(DB_PATH)

    return {
        "ollama_connected": ollama_running,
        "models_available": models,
        "database_size_bytes": db_size,
        "registered_clients": client_count,
        "registered_matters": matter_count,
        "vault_document_count": doc_count
    }

@router.get("/system/upcoming-hearings")
def get_upcoming_hearings(hours: int = 48, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from aegis_backend.database import Schedule
    now = datetime.now(timezone.utc).isoformat()
    cutoff = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    schedules = db.query(Schedule).filter(
        Schedule.is_completed == False,
        Schedule.target_date >= now,
        Schedule.target_date <= cutoff
    ).order_by(Schedule.target_date).all()
    return [
        {"id": s.id, "title": s.title, "schedule_type": s.schedule_type, "target_date": s.target_date}
        for s in schedules
    ]
