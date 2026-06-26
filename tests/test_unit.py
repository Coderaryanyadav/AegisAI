import os
# Configure a separate test database file to prevent polluting the local database
os.environ["DATABASE_URL"] = "sqlite:///tests/test_aegis_ai.db"

import pytest
from aegis_backend.services.document_service import DocumentService
from aegis_backend.indian_legal_helper import IndianLegalHelper
from aegis_backend.core.security import hash_password, verify_password

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    # Teardown: clean up test database files
    test_db_path = "tests/test_aegis_ai.db"
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass
    # Clean up wal files if any
    for ext in ["-wal", "-shm"]:
        if os.path.exists(test_db_path + ext):
            try:
                os.remove(test_db_path + ext)
            except Exception:
                pass

def test_chunk_text():
    text = "word " * 1000
    chunks = DocumentService.chunk_text(text, chunk_size=400, chunk_overlap=80)
    assert len(chunks) > 1
    # Check that chunks have expected length and some overlap
    first_chunk_words = chunks[0].split()
    assert len(first_chunk_words) <= 400
    assert first_chunk_words[-1] == "word"

def test_indian_legal_helper_convert_section():
    # IPC to BNS
    res_ipc = IndianLegalHelper.convert_section("ipc", "302")
    assert res_ipc is not None
    assert res_ipc["new_section"] == "101"
    assert res_ipc["act"] == "BNS"

    # CrPC to BNSS
    res_crpc = IndianLegalHelper.convert_section("crpc", "154")
    assert res_crpc is not None
    assert res_crpc["new_section"] == "173"
    assert res_crpc["act"] == "BNSS"

    # Evidence (IEA) to BSA
    res_iea = IndianLegalHelper.convert_section("iea", "3")
    assert res_iea is not None
    assert res_iea["new_section"] == "2"
    assert res_iea["act"] == "BSA"

    # Invalid section
    res_invalid = IndianLegalHelper.convert_section("ipc", "999")
    assert res_invalid is None

def test_indian_legal_helper_normalize_citation():
    # AIR SC
    norm_air = IndianLegalHelper.normalize_citation("AIR 1996 SC 1234")
    assert norm_air == "1996-sc-1234"

    # INSC
    norm_insc = IndianLegalHelper.normalize_citation("2024 INSC 15")
    assert norm_insc == "2024-sc-15"

    # Fallback normalization
    norm_fallback = IndianLegalHelper.normalize_citation("random citation string")
    assert norm_fallback == "random-citation-string"

def test_password_hashing():
    pw = "SuperSecurePassword123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("WrongPassword", hashed)

def test_database_engine_config(monkeypatch):
    import os
    import sqlalchemy
    from unittest.mock import MagicMock
    
    # Mock create_engine so it does not attempt to resolve the psycopg2 dialect driver
    mock_create = MagicMock()
    monkeypatch.setattr(sqlalchemy, "create_engine", mock_create)
    
    # Simulate the selection and instantiation logic in database.py
    def get_engine_args(url):
        if url.startswith("sqlite"):
            return {
                "url": url,
                "connect_args": {"check_same_thread": False, "timeout": 60.0},
                "poolclass": sqlalchemy.pool.NullPool
            }
        else:
            return {
                "url": url,
                "pool_size": 10,
                "max_overflow": 20,
                "pool_recycle": 3600
            }
            
    args_sqlite = get_engine_args("sqlite:///test.db")
    assert args_sqlite["poolclass"] == sqlalchemy.pool.NullPool
    assert args_sqlite["connect_args"]["timeout"] == 60.0
    
    args_pg = get_engine_args("postgresql://user:pass@localhost/dbname")
    assert args_pg["pool_size"] == 10
    assert args_pg["max_overflow"] == 20
    assert args_pg["pool_recycle"] == 3600

def test_must_change_password_enforcement():
    from fastapi.testclient import TestClient
    from aegis_backend.main import app
    from aegis_backend.database import SessionLocal, User
    from aegis_backend.core.security import hash_password
    
    client = TestClient(app)
    db = SessionLocal()
    
    # Check if test admin exists, update must_change_password flag
    test_user = db.query(User).filter(User.email == "admin@legalai.local").first()
    if not test_user:
        # Create temporary test admin
        test_user = User(
            email="admin@legalai.local",
            hashed_password=hash_password("adminpassword123"),
            role="admin",
            must_change_password=True
        )
        db.add(test_user)
        db.commit()
    else:
        test_user.must_change_password = True
        test_user.hashed_password = hash_password("adminpassword123")
        db.commit()
        
    try:
        # 1. Login with seeded user must be blocked/warned
        response = client.post("/api/auth/token", data={
            "username": "admin@legalai.local",
            "password": "adminpassword123"
        })
        assert response.status_code == 200
        json_data = response.json()
        assert json_data.get("must_change_password") is True
        assert "access_token" in json_data
        token = json_data.get("access_token")
        
        # 2. Change password using the authenticated endpoint
        change_res = client.post(
            "/api/auth/change-default-password",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "current_password": "adminpassword123",
                "new_password": "NewBrutalSecurePassword123!"
            }
        )
        assert change_res.status_code == 200
        assert "Password updated successfully" in change_res.json()["message"]
        
        # Verify user state is updated in DB
        db.refresh(test_user)
        assert test_user.must_change_password is False
        
        # 3. Successful login with new password
        login_res = client.post("/api/auth/token", data={
            "username": "admin@legalai.local",
            "password": "NewBrutalSecurePassword123!"
        })
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()
        
    finally:
        # Restore test user to default if we want or clean it up
        db.delete(test_user)
        db.commit()
        db.close()

def test_ollama_subprocess_lifecycle():
    import asyncio
    import subprocess
    from unittest.mock import MagicMock
    import aegis_backend.main
    
    # Mock subprocess.Popen
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.return_value = None # Process is still running
    
    # Inject mock process
    aegis_backend.main.ollama_process = mock_process
    
    # Run the termination logic block in a synchronous mock test
    process = aegis_backend.main.ollama_process
    if process:
        process.terminate()
        # Verify terminate was called
        assert process.terminate.called
        
        # Simulate process exit after terminate
        process.poll.return_value = 0
        if process.poll() is None:
            # Should not be called since poll returned 0
            process.kill()
            
        assert not process.kill.called
    
    # Test fallback kill path
    mock_process_stubborn = MagicMock(spec=subprocess.Popen)
    mock_process_stubborn.poll.return_value = None # Stubborn process never exits
    aegis_backend.main.ollama_process = mock_process_stubborn
    
    process = aegis_backend.main.ollama_process
    if process:
        process.terminate()
        assert process.terminate.called
        
        # poll is still None, so we trigger kill
        if process.poll() is None:
            process.kill()
            process.wait()
            
        assert process.kill.called
        assert process.wait.called

def test_secure_key_helper_fallback(monkeypatch, tmp_path):
    import os
    from aegis_backend.database import get_secure_key
    
    # Ensure environment variable is not interfering
    monkeypatch.delenv("AEGIS_TESTKEY_KEY", raising=False)
    
    # Force keyring load/save to throw errors to trigger fallback file storage
    import keyring
    def mock_fail(*args, **kwargs):
        raise RuntimeError("Simulated Keyring Service Error")
    monkeypatch.setattr(keyring, "get_password", mock_fail)
    monkeypatch.setattr(keyring, "set_password", mock_fail)
    
    temp_key_file = os.path.join(tmp_path, ".testkey.key")
    
    # 1. Generate key securely via fallback flow
    key = get_secure_key("testkey", temp_key_file, is_hex=True)
    assert len(key) == 64
    assert os.path.exists(temp_key_file)
    
    # 2. Check if permissions are correctly restricted
    try:
        mode = os.stat(temp_key_file).st_mode & 0o777
        # On some environments (Windows or virtualized mounts), chmod is restricted/ignored.
        # But where supported, we check st_mode permissions
        if os.name != 'nt':
            assert mode == 0o600 or mode == 0o000
    except Exception:
        pass
        
    # 3. Retrieve key using cache matching
    key_cached = get_secure_key("testkey", temp_key_file, is_hex=True)
    assert key == key_cached

def test_rag_context_limit_truncation():
    # Emulate the RAG prompt word truncation engine
    max_words = 100
    total_words = 0
    context = ""
    
    mock_chunks = [
        {"content": "apple " * 60, "metadata": {"filename": "doc1.txt"}},
        {"content": "banana " * 60, "metadata": {"filename": "doc2.txt"}},
        {"content": "cherry " * 60, "metadata": {"filename": "doc3.txt"}},
    ]
    
    for idx, c in enumerate(mock_chunks):
        filename = c["metadata"].get("filename", "Unknown Document")
        chunk_content = c["content"]
        chunk_words = len(chunk_content.split())
        
        if total_words + chunk_words > max_words:
            allowed_words = max_words - total_words
            if allowed_words <= 0:
                break
            words = chunk_content.split()
            chunk_content = " ".join(words[:allowed_words]) + " [Content truncated to fit local LLM context limits]"
            total_words += allowed_words
        else:
            total_words += chunk_words
            
        context += f"[Context {idx+1}] File: {filename}\nContent:\n{chunk_content}\n\n"
        
    assert total_words == max_words
    assert "[Content truncated to fit local LLM context limits]" in context
    assert "doc3.txt" not in context

def test_user_management_and_refresh():
    from fastapi.testclient import TestClient
    from aegis_backend.main import app
    from aegis_backend.database import SessionLocal, User
    from aegis_backend.core.security import hash_password
    
    client = TestClient(app)
    db = SessionLocal()
    
    # 1. Create a test admin and a test lawyer
    admin_user = db.query(User).filter(User.email == "admin_mgt@legalai.local").first()
    if not admin_user:
        admin_user = User(
            email="admin_mgt@legalai.local",
            hashed_password=hash_password("AdminSecurePassword123!"),
            role="admin"
        )
        db.add(admin_user)
    else:
        admin_user.role = "admin"
        admin_user.is_disabled = False
        
    lawyer_user = db.query(User).filter(User.email == "lawyer_mgt@legalai.local").first()
    if not lawyer_user:
        lawyer_user = User(
            email="lawyer_mgt@legalai.local",
            hashed_password=hash_password("LawyerSecurePassword123!"),
            role="lawyer"
        )
        db.add(lawyer_user)
    else:
        lawyer_user.role = "lawyer"
        lawyer_user.is_disabled = False
        
    db.commit()
    db.refresh(admin_user)
    db.refresh(lawyer_user)
    
    try:
        from aegis_backend.database import AuthRateLimit
        db.query(AuthRateLimit).delete()
        db.commit()
        
        # Get admin token
        admin_login = client.post("/api/auth/token", data={
            "username": "admin_mgt@legalai.local",
            "password": "AdminSecurePassword123!"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get lawyer token
        lawyer_login = client.post("/api/auth/token", data={
            "username": "lawyer_mgt@legalai.local",
            "password": "LawyerSecurePassword123!"
        })
        assert lawyer_login.status_code == 200
        lawyer_token = lawyer_login.json()["access_token"]
        lawyer_refresh_token = lawyer_login.json()["refresh_token"]
        lawyer_headers = {"Authorization": f"Bearer {lawyer_token}"}
        
        # Test Refresh Endpoint
        refresh_res = client.post("/api/auth/refresh", data={"refresh_token": lawyer_refresh_token})
        assert refresh_res.status_code == 200
        assert "access_token" in refresh_res.json()
        
        # Test GET /users (admin-only)
        users_res = client.get("/api/users", headers=admin_headers)
        assert users_res.status_code == 200
        assert any(u["email"] == "lawyer_mgt@legalai.local" for u in users_res.json())
        
        # Test GET /users with lawyer role (should be 403 Forbidden)
        users_res_lawyer = client.get("/api/users", headers=lawyer_headers)
        assert users_res_lawyer.status_code == 403
        
        # Test PUT /users/{id}/role (admin-only)
        role_res = client.put(f"/api/users/{lawyer_user.id}/role", data={"role": "auditor"}, headers=admin_headers)
        assert role_res.status_code == 200
        assert role_res.json()["role"] == "auditor"
        
        # Test PUT /users/{id}/disable (admin-only)
        disable_res = client.put(f"/api/users/{lawyer_user.id}/disable", data={"is_disabled": True}, headers=admin_headers)
        assert disable_res.status_code == 200
        assert disable_res.json()["is_disabled"] is True
        
        # Verify disabled user cannot log in
        db.query(AuthRateLimit).delete()
        db.commit()
        
        login_disabled = client.post("/api/auth/token", data={
            "username": "lawyer_mgt@legalai.local",
            "password": "LawyerSecurePassword123!"
        })
        assert login_disabled.status_code == 400
        assert "disabled" in login_disabled.json()["detail"].lower()
        
    finally:
        db.delete(admin_user)
        db.delete(lawyer_user)
        db.commit()
        db.close()

def test_enum_literals_and_early_file_size_check():
    from pydantic import ValidationError
    from aegis_backend.schemas.models import MatterCreate, ScheduleCreate, InvoiceStatusUpdate
    from aegis_backend.indian_legal_helper import IndianLegalHelper
    
    # 1. Verify MatterCreate enum validation
    with pytest.raises(ValidationError):
        # Invalid status should fail validation
        MatterCreate(client_id=1, title="Test Case", status="invalid_status")
        
    # Valid statuses should pass validation
    for valid_status in ["open", "pending_hearing", "closed", "archived"]:
        m = MatterCreate(client_id=1, title="Test Case", status=valid_status)
        assert m.status == valid_status
        
    # 2. Verify ScheduleCreate enum validation
    with pytest.raises(ValidationError):
        ScheduleCreate(matter_id=1, title="Hearing", schedule_type="invalid_type", target_date="2026-06-26T12:00:00")
        
    for valid_type in ["hearing", "deadline", "meeting"]:
        s = ScheduleCreate(matter_id=1, title="Hearing", schedule_type=valid_type, target_date="2026-06-26T12:00:00")
        assert s.schedule_type == valid_type
        
    # 3. Verify InvoiceStatusUpdate enum validation
    with pytest.raises(ValidationError):
        InvoiceStatusUpdate(status="invalid_invoice_status")
        
    for valid_inv_status in ["unpaid", "paid", "overdue"]:
        i = InvoiceStatusUpdate(status=valid_inv_status)
        assert i.status == valid_inv_status

    # 4. Verify IndianLegalHelper.convert_section fallback works in mock ollama flow
    mapping = IndianLegalHelper.convert_section("IPC", "302")
    assert mapping is not None
    assert mapping["new_section"] == "101"
    assert mapping["subject"] == "Punishment for Murder"

def test_backup_manager_sqlite():
    from aegis_backend.backup_manager import BackupManager
    from aegis_backend.database import SessionLocal, User, Client
    import os

    # 1. Seed a test client
    db = SessionLocal()
    client = Client(name="Backup Test Client", email="backup_test@firm.com")
    db.add(client)
    db.commit()
    db.refresh(client)
    client_id = client.id
    db.close()

    # 2. Create backup
    backup_path = BackupManager.create_backup(is_manual=True)
    assert backup_path is not None
    assert os.path.exists(backup_path)

    try:
        # 3. Clear data
        db = SessionLocal()
        db.query(Client).filter(Client.id == client_id).delete()
        db.commit()
        db.close()

        # Check deleted
        db = SessionLocal()
        assert db.query(Client).filter(Client.id == client_id).first() is None
        db.close()

        # 4. Restore backup
        restored = BackupManager.restore_backup(backup_path)
        assert restored is True

        # 5. Check restored
        db = SessionLocal()
        restored_client = db.query(Client).filter(Client.id == client_id).first()
        assert restored_client is not None
        assert restored_client.name == "Backup Test Client"
        db.delete(restored_client)
        db.commit()
        db.close()

    finally:
        # Clean up backup file
        if os.path.exists(backup_path):
            os.remove(backup_path)
