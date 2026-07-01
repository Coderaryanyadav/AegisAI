import os
import shutil
import asyncio
import logging
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from aegis_backend.database import AEGIS_DIR, Document, Schedule, Matter, Client, AuditLog
from aegis_backend.backup_manager import BackupManager
from aegis_backend.vector_store import vector_store

logger = logging.getLogger("aegis_ai.backup_service")

class BackupService:
    @staticmethod
    async def get_backup_history(db: AsyncSession, skip: int = 0, limit: int = 100):
        from aegis_backend.database import BackupHistory
        from sqlalchemy import select

        stmt = select(BackupHistory).order_by(BackupHistory.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def create_backup(is_manual: bool = True, destination_dir: str = None) -> str:
        return await asyncio.to_thread(
            BackupManager.create_backup,
            destination_dir,
            is_manual
        )

    @staticmethod
    async def restore_backup(backup_path: str) -> None:
        await asyncio.to_thread(BackupManager.restore_backup, backup_path)

    @staticmethod
    async def perform_panic_wipe(db: AsyncSession) -> str:
        emergency_backup_dir = os.path.join(AEGIS_DIR, "emergency")
        os.makedirs(emergency_backup_dir, exist_ok=True)

        backup_path = await asyncio.to_thread(
            BackupManager.create_backup,
            emergency_backup_dir,
            True
        )

        await db.execute(delete(Document))
        await db.execute(delete(Schedule))
        await db.execute(delete(Matter))
        await db.execute(delete(Client))
        await db.execute(delete(AuditLog))
        await db.commit()

        await asyncio.to_thread(BackupService._shred_files)
        vector_store.reset_collection()

        return backup_path

    @staticmethod
    def _shred_files():
        vault_dir = os.path.join(AEGIS_DIR, "vault")
        if os.path.exists(vault_dir):
            for filename in os.listdir(vault_dir):
                file_path = os.path.join(vault_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        file_size = os.path.getsize(file_path)
                        with open(file_path, "ba+", buffering=0) as f_shred:
                            f_shred.write(os.urandom(file_size))
                    except Exception:
                        pass
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

        chroma_dir = os.path.join(AEGIS_DIR, "chroma")
        if os.path.exists(chroma_dir):
            for root, _, files in os.walk(chroma_dir):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    if os.path.isfile(file_path):
                        try:
                            file_size = os.path.getsize(file_path)
                            with open(file_path, "ba+", buffering=0) as f_shred:
                                f_shred.write(os.urandom(file_size))
                        except Exception:
                            pass
            shutil.rmtree(chroma_dir, ignore_errors=True)
            os.makedirs(chroma_dir, exist_ok=True)
