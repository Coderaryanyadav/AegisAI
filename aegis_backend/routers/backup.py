import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from aegis_backend.database import get_db, User, BackupHistory, Document, Schedule, Matter, Client, AuditLog, AEGIS_DIR
from aegis_backend.core.security import get_current_user, verify_admin, log_audit_trail
from aegis_backend.backup_manager import BackupManager
from aegis_backend.vector_store import vector_store

router = APIRouter(tags=["backup"])

@router.get("/backup/history")
async def get_backup_runs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    stmt = select(BackupHistory).order_by(BackupHistory.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/backup/create")
def trigger_manual_backup(current_user: User = Depends(verify_admin)):
    try:
        backup_path = BackupManager.create_backup(is_manual=True)
        return {"status": "success", "path": backup_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup generation failed: {e}")

@router.post("/backup/restore")
def trigger_restore(backup_path: str, current_user: User = Depends(verify_admin)):
    try:
        # Extract filename only to eliminate any directory traversal vulnerability
        safe_filename = os.path.basename(backup_path)
        candidate = os.path.abspath(os.path.join(AEGIS_DIR, "backups", safe_filename))

        backups_dir = os.path.abspath(os.path.join(AEGIS_DIR, "backups"))
        if not os.path.commonpath([candidate, backups_dir]) == backups_dir:
            raise HTTPException(status_code=400, detail="Invalid backup path")

        BackupManager.restore_backup(candidate)
        return {"status": "success", "message": "Restore completed. Application state reverted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restoration failed: {e}")

@router.post("/backup/panic", status_code=200)
async def emergency_panic_button(db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    import logging
    logger = logging.getLogger("aegis_ai.backend")
    logger.warning("PANIC SIGNAL INITIATED: Wiping active workspace contents.")
    try:
        # Create emergency recovery point
        emergency_backup_dir = os.path.join(AEGIS_DIR, "emergency")
        os.makedirs(emergency_backup_dir, exist_ok=True)
        backup_path = BackupManager.create_backup(destination_dir=emergency_backup_dir, is_manual=True)
        
        # WIPE DB tables containing client secrets
        await db.execute(delete(Document))
        await db.execute(delete(Schedule))
        await db.execute(delete(Matter))
        await db.execute(delete(Client))
        await db.execute(delete(AuditLog))
        await db.commit()

        # Securely shred document vault files
        vault_dir = os.path.join(AEGIS_DIR, "vault")
        if os.path.exists(vault_dir):
            for f in os.listdir(vault_dir):
                file_path = os.path.join(vault_dir, f)
                if os.path.isfile(file_path):
                    # Shredding: Overwrite file with random bytes before deleting
                    file_size = os.path.getsize(file_path)
                    try:
                        with open(file_path, "ba+", buffering=0) as f_shred:
                            f_shred.write(os.urandom(file_size))
                    except Exception:
                        pass
                    os.remove(file_path)

        # Shred and wipe chroma collections
        chroma_dir = os.path.join(AEGIS_DIR, "chroma")
        if os.path.exists(chroma_dir):
            for root, dirs, files in os.walk(chroma_dir):
                for f in files:
                    file_path = os.path.join(root, f)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        try:
                            with open(file_path, "ba+", buffering=0) as f_shred:
                                f_shred.write(os.urandom(file_size))
                        except Exception:
                            pass
            shutil.rmtree(chroma_dir)
            os.makedirs(chroma_dir, exist_ok=True)
            
        vector_store.reset_collection()

        logger.warning("PANIC PROCESS COMPLETED. All client secrets eradicated from active workspace.")
        return {
            "status": "panic_complete",
            "message": f"Active records scrubbed. Sealed recovery archive created at: {backup_path}"
        }
    except Exception as e:
        logger.error(f"Panic recovery routine failed: {e}")
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Panic wipe routine encountered error: {e}")

