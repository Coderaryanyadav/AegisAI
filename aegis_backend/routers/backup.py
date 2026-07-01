import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_backend.database import get_db, User, BackupHistory, AEGIS_DIR
from aegis_backend.core.security import verify_admin
from aegis_backend.services.backup_service import BackupService

router = APIRouter(tags=["backup"])

@router.get("/backup/history")
async def get_backup_runs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    return await BackupService.get_backup_history(db, skip=skip, limit=limit)

@router.post("/backup/create")
async def trigger_manual_backup(current_user: User = Depends(verify_admin)):
    try:
        backup_path = await BackupService.create_backup(is_manual=True)
        return {"status": "success", "path": backup_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup generation failed: {e}")

@router.post("/backup/restore")
async def trigger_restore(backup_path: str, current_user: User = Depends(verify_admin)):
    try:
        # Extract filename only to eliminate any directory traversal vulnerability
        safe_filename = os.path.basename(backup_path)
        candidate = os.path.abspath(os.path.join(AEGIS_DIR, "backups", safe_filename))

        backups_dir = os.path.abspath(os.path.join(AEGIS_DIR, "backups"))
        if not os.path.commonpath([candidate, backups_dir]) == backups_dir:
            raise HTTPException(status_code=400, detail="Invalid backup path")

        await BackupService.restore_backup(candidate)
        return {"status": "success", "message": "Restore completed. Application state reverted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restoration failed: {e}")

@router.post("/backup/panic", status_code=200)
async def emergency_panic_button(db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_admin)):
    try:
        backup_path = await BackupService.perform_panic_wipe(db)
        return {
            "status": "panic_complete",
            "message": f"Active records scrubbed. Sealed recovery archive created at: {backup_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Panic wipe routine encountered error: {e}")

