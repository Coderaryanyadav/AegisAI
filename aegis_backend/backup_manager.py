import os
import zipfile
import shutil
import base64
import time
import asyncio
import logging
import sqlite3
import tempfile
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from aegis_backend.database import (
    AEGIS_DIR, DB_PATH, KEY_PATH, SessionLocal, BackupHistory
)

logger = logging.getLogger("aegis_ai.backup_manager")

class BackupManager:
    """Manages 100% offline, AES-256 GCM encrypted backups and restore points."""

    @staticmethod
    def get_aes_key() -> bytes:
        """Loads and returns raw 32-byte key for AES-256 GCM."""
        if not os.path.exists(KEY_PATH):
            raise FileNotFoundError(f"Master key file not found: {KEY_PATH}")
        with open(KEY_PATH, "rb") as f:
            fernet_key = f.read()
        # Decode url-safe base64 key to get raw 32 bytes
        return base64.urlsafe_b64decode(fernet_key)

    @classmethod
    def encrypt_data(cls, data: bytes) -> bytes:
        """Encrypts bytes using AES-256 GCM."""
        key = cls.get_aes_key()
        nonce = os.urandom(12)
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        # Pack nonce + tag + ciphertext
        return nonce + encryptor.tag + ciphertext

    @classmethod
    def decrypt_data(cls, encrypted_data: bytes) -> bytes:
        """Decrypts bytes using AES-256 GCM."""
        if len(encrypted_data) < 28:
            raise ValueError("Encrypted data too short or corrupt.")
        key = cls.get_aes_key()
        nonce = encrypted_data[:12]
        tag = encrypted_data[12:28]
        ciphertext = encrypted_data[28:]
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    @classmethod
    def create_backup(cls, destination_dir: str = None, is_manual: bool = True) -> str:
        """
        Creates an encrypted ZIP backup containing database, chroma vector store, and document vault.
        Saves backup log in SQLite.
        """
        if not destination_dir:
            destination_dir = os.path.join(AEGIS_DIR, "backups")
        os.makedirs(destination_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"aegis_backup_{timestamp}.enc"
        backup_path = os.path.join(destination_dir, backup_name)

        db = SessionLocal()
        
        # Temp dir for creating the zip
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. Safely copy the SQLite database using backup API
                temp_db_path = os.path.join(temp_dir, "aegis_ai.db")
                src_conn = sqlite3.connect(DB_PATH)
                dest_conn = sqlite3.connect(temp_db_path)
                with dest_conn:
                    src_conn.backup(dest_conn)
                dest_conn.close()
                src_conn.close()

                # 2. Paths to package
                vault_dir = os.path.join(AEGIS_DIR, "vault")
                chroma_dir = os.path.join(AEGIS_DIR, "chroma")

                temp_zip_path = os.path.join(temp_dir, "archive.zip")

                # Create the ZIP
                with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add SQLite database
                    zipf.write(temp_db_path, "aegis_ai.db")
                    
                    # Add document vault
                    if os.path.exists(vault_dir):
                        for root, _, files in os.walk(vault_dir):
                            for file in files:
                                full_p = os.path.join(root, file)
                                rel_p = os.path.relpath(full_p, AEGIS_DIR)
                                zipf.write(full_p, rel_p)

                    # Add chroma vector store
                    if os.path.exists(chroma_dir):
                        for root, _, files in os.walk(chroma_dir):
                            for file in files:
                                full_p = os.path.join(root, file)
                                rel_p = os.path.relpath(full_p, AEGIS_DIR)
                                zipf.write(full_p, rel_p)

                # 3. Read raw ZIP, encrypt and write to target path
                with open(temp_zip_path, "rb") as f:
                    zip_data = f.read()

                encrypted_data = cls.encrypt_data(zip_data)
                
                with open(backup_path, "wb") as f:
                    f.write(encrypted_data)

                size_bytes = len(encrypted_data)
                logger.info(f"Backup created successfully: {backup_path} ({size_bytes} bytes)")

                # Record history
                history = BackupHistory(
                    backup_name=backup_name,
                    backup_size_bytes=size_bytes,
                    destination_path=backup_path,
                    is_manual=is_manual,
                    status="success"
                )
                db.add(history)
                db.commit()
                return backup_path

            except Exception as e:
                logger.error(f"Backup creation failed: {e}")
                try:
                    db.rollback()
                except Exception:
                    pass
                history = BackupHistory(
                    backup_name=backup_name,
                    backup_size_bytes=0,
                    destination_path=backup_path,
                    is_manual=is_manual,
                    status="failed",
                    error_message=str(e)
                )
                try:
                    db.add(history)
                    db.commit()
                except Exception:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                raise e
            finally:
                db.close()

    @classmethod
    def restore_backup(cls, backup_path: str) -> bool:
        """
        Decrypts and restores database, document vault, and chroma vector db.
        Replaces existing files safely.
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        logger.info(f"Initiating restore from backup: {backup_path}")

        try:
            with open(backup_path, "rb") as f:
                encrypted_data = f.read()

            # Decrypt backup zip file
            zip_data = cls.decrypt_data(encrypted_data)

            # Temp dir to extract contents
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_zip_path = os.path.join(temp_dir, "archive.zip")
                with open(temp_zip_path, "wb") as f:
                    f.write(zip_data)

                # Extract
                with zipfile.ZipFile(temp_zip_path, 'r') as zipf:
                    zipf.extractall(temp_dir)

                # Validate database exists in archive
                archived_db_path = os.path.join(temp_dir, "aegis_ai.db")
                if not os.path.exists(archived_db_path):
                    raise ValueError("Backup archive does not contain a valid database file.")

                # Close database connection engine or perform restoration carefully
                # For safety under desktop setup, we copy the new SQLite DB over the old one.
                # First delete existing files to prevent active lock clashes
                vault_dir = os.path.join(AEGIS_DIR, "vault")
                chroma_dir = os.path.join(AEGIS_DIR, "chroma")

                # Restore DB file
                shutil.copy2(archived_db_path, DB_PATH)

                # Restore Vault
                archived_vault_dir = os.path.join(temp_dir, "vault")
                if os.path.exists(archived_vault_dir):
                    if os.path.exists(vault_dir):
                        shutil.rmtree(vault_dir)
                    shutil.copytree(archived_vault_dir, vault_dir)

                # Restore Chroma
                archived_chroma_dir = os.path.join(temp_dir, "chroma")
                if os.path.exists(archived_chroma_dir):
                    if os.path.exists(chroma_dir):
                        shutil.rmtree(chroma_dir)
                    shutil.copytree(archived_chroma_dir, chroma_dir)

            logger.info("Restoration completed successfully.")
            return True
        except Exception as e:
            logger.error(f"Restoration failed: {e}")
            raise e


async def run_backup_scheduler(interval_seconds: int = 3600, retention_limit: int = 5):
    """
    Background loop that runs automated snapshots periodically.
    Prunes oldest backups beyond the retention limit.
    """
    logger.info("AegisAI Backup Scheduler daemon started.")
    while True:
        try:
            # Create automated backup in a thread to avoid blocking the event loop
            await asyncio.to_thread(BackupManager.create_backup, None, False)

            # Prune old automated backups
            db = SessionLocal()
            try:
                # Find all automated backups, ordered oldest first
                automated_backups = db.query(BackupHistory).filter(
                    BackupHistory.is_manual == False,
                    BackupHistory.status == "success"
                ).order_by(BackupHistory.created_at.asc()).all()

                if len(automated_backups) > retention_limit:
                    to_delete_count = len(automated_backups) - retention_limit
                    for i in range(to_delete_count):
                        target = automated_backups[i]
                        if os.path.exists(target.destination_path):
                            os.remove(target.destination_path)
                            logger.info(f"Pruned old automated backup file: {target.destination_path}")
                        
                        db.delete(target)
                    db.commit()
            except Exception as pe:
                logger.error(f"Error during backup pruning: {pe}")
                try:
                    db.rollback()
                except Exception:
                    pass
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Backup scheduler encountered an error: {e}")

        await asyncio.sleep(interval_seconds)
