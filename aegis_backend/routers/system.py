import os
import sys
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_backend.database import get_db, User, Document, Matter, Client, AuditLog, AEGIS_DIR, DB_PATH
from aegis_backend.core import security
from aegis_backend.core.security import get_current_user, verify_admin
from aegis_backend.ollama_service import OllamaService

router = APIRouter(tags=["system"])

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
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
async def get_compliance_audit_logs(response: Response, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    from aegis_backend.core.security import verify_audit_trail_integrity
    
    count_stmt = select(func.count(AuditLog.id))
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar()
    response.headers["X-Total-Count"] = str(total_count)
    
    integrity_passed = await verify_audit_trail_integrity(db)
    response.headers["X-Audit-Log-Integrity"] = "PASSED" if integrity_passed else "FAILED_TAMPERED"
    
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    res = await db.execute(stmt.offset(skip).limit(limit))
    return res.scalars().all()

@router.get("/system/audit-logs/export")
async def export_signed_audit_logs(db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    res = await db.execute(stmt)
    logs = res.scalars().all()
    
    report_lines = []
    report_lines.append("================================================================================")
    report_lines.append("                       AEGIS LEGAL AI COMPLIANCE AUDIT REPORT                   ")
    report_lines.append("================================================================================")
    from aegis_backend.core.security import verify_audit_trail_integrity
    integrity_passed = await verify_audit_trail_integrity(db)
    report_lines.append(f"Exported At: {datetime.now(timezone.utc).isoformat()} UTC")
    report_lines.append(f"Exported By: {current_user.email}")
    report_lines.append(f"System Directory: {AEGIS_DIR}")
    report_lines.append(f"Integrity Chain: {'VERIFIED/SECURE' if integrity_passed else 'WARNING: TAMPERING DETECTED'}")
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
    
    from aegis_backend.database import master_key
    master_key_bytes = master_key.encode("utf-8") if isinstance(master_key, str) else master_key
    signature = hmac.new(master_key_bytes, report_content.encode("utf-8"), hashlib.sha256).hexdigest()
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
async def system_diagnostics(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    models = await OllamaService.get_available_models()
    ollama_running = len(models) > 0

    doc_res = await db.execute(select(func.count(Document.id)))
    doc_count = doc_res.scalar()
    
    matter_res = await db.execute(select(func.count(Matter.id)))
    matter_count = matter_res.scalar()
    
    client_res = await db.execute(select(func.count(Client.id)))
    client_count = client_res.scalar()

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
async def get_upcoming_hearings(hours: int = 48, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from aegis_backend.database import Schedule
    now = datetime.now(timezone.utc).isoformat()
    cutoff = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    
    stmt = select(Schedule).filter(
        Schedule.is_completed == False,
        Schedule.target_date >= now,
        Schedule.target_date <= cutoff
    ).order_by(Schedule.target_date)
    
    res = await db.execute(stmt)
    schedules = res.scalars().all()
    return [
        {"id": s.id, "title": s.title, "schedule_type": s.schedule_type, "target_date": s.target_date}
        for s in schedules
    ]

