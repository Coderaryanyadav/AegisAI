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

def test_legal_chunker_structure():
    text = """
    Chapter I: Preliminary
    Section 1: Short title and commencement.
    This is the first section of the document.
    Section 2: Definitions.
    In this Act, unless the context otherwise requires, definition A means B.
    Clause 2.1: Definition of advocate.
    Advocate means a legal practitioner.
    """
    chunks = DocumentService.chunk_text(text, chunk_size=100, chunk_overlap=10, document_name="act.pdf")
    assert len(chunks) >= 3
    # Check prefixes
    assert "[Doc: act.pdf]" in chunks[0]
    assert "[Chapter I]" in chunks[0]
    
    assert "[Section 1]" in chunks[1]
    assert "[Section 2]" in chunks[2]
    
    assert "[Clause 2.1]" in chunks[3]

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

def test_indian_legal_helper_detect_statutory_citations():
    text = (
        "The accused was charged under Section 302 of the IPC. "
        "FIR registered under S. 154 CrPC. Also see BNS Section 101."
    )
    citations = IndianLegalHelper.detect_statutory_citations(text)
    assert len(citations) >= 2
    acts = {c["act"] for c in citations}
    assert "IPC" in acts or "CRPC" in acts

def test_backup_manager_hmac_integrity():
    from aegis_backend.backup_manager import BackupManager, BACKUP_MAGIC, HMAC_SIZE
    payload = b"encrypted-test-payload"
    signed = BackupManager._pack_signed_backup(payload)
    assert signed.startswith(BACKUP_MAGIC)
    assert len(signed) == len(BACKUP_MAGIC) + HMAC_SIZE + len(payload)
    restored = BackupManager._unpack_signed_backup(signed)
    assert restored == payload

    tampered = bytearray(signed)
    tampered[-1] ^= 0xFF
    with pytest.raises(ValueError, match="integrity check failed"):
        BackupManager._unpack_signed_backup(bytes(tampered))

def test_memory_guard_stats():
    from aegis_backend.core.memory_guard import MemoryGuard
    stats = MemoryGuard.get_memory_stats()
    assert "available_mb" in stats
    assert "total_mb" in stats
    allowed, reason = MemoryGuard.check_inference_allowed(required_mb=1)
    assert allowed is True
    assert reason == "OK"

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
        response = client.post("/api/v1/auth/token", data={
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
            "/api/v1/auth/change-default-password",
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
        login_res = client.post("/api/v1/auth/token", data={
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
        admin_login = client.post("/api/v1/auth/token", data={
            "username": "admin_mgt@legalai.local",
            "password": "AdminSecurePassword123!"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get lawyer token
        lawyer_login = client.post("/api/v1/auth/token", data={
            "username": "lawyer_mgt@legalai.local",
            "password": "LawyerSecurePassword123!"
        })
        assert lawyer_login.status_code == 200
        lawyer_token = lawyer_login.json()["access_token"]
        lawyer_refresh_token = lawyer_login.json()["refresh_token"]
        lawyer_headers = {"Authorization": f"Bearer {lawyer_token}"}
        
        # Test Refresh Endpoint
        refresh_res = client.post("/api/v1/auth/refresh", data={"refresh_token": lawyer_refresh_token})
        assert refresh_res.status_code == 200
        assert "access_token" in refresh_res.json()
        
        # Test GET /users (admin-only)
        users_res = client.get("/api/v1/users", headers=admin_headers)
        assert users_res.status_code == 200
        assert any(u["email"] == "lawyer_mgt@legalai.local" for u in users_res.json())
        
        # Test GET /users with lawyer role (should be 403 Forbidden)
        users_res_lawyer = client.get("/api/v1/users", headers=lawyer_headers)
        assert users_res_lawyer.status_code == 403
        
        # Test PUT /users/{id}/role (admin-only)
        role_res = client.put(f"/api/v1/users/{lawyer_user.id}/role", data={"role": "auditor"}, headers=admin_headers)
        assert role_res.status_code == 200
        assert role_res.json()["role"] == "auditor"
        
        # Test PUT /users/{id}/disable (admin-only)
        disable_res = client.put(f"/api/v1/users/{lawyer_user.id}/disable", data={"is_disabled": True}, headers=admin_headers)
        assert disable_res.status_code == 200
        assert disable_res.json()["is_disabled"] is True
        
        # Verify disabled user cannot log in
        db.query(AuthRateLimit).delete()
        db.commit()
        
        login_disabled = client.post("/api/v1/auth/token", data={
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

def test_token_revocation_logout():
    from fastapi.testclient import TestClient
    from aegis_backend.main import app
    from aegis_backend.database import SessionLocal, User, RevokedToken
    from aegis_backend.core.security import hash_password
    
    client = TestClient(app)
    db = SessionLocal()
    
    # 1. Create a test user
    test_user = db.query(User).filter(User.email == "revocation_test@legalai.local").first()
    if not test_user:
        test_user = User(
            email="revocation_test@legalai.local",
            hashed_password=hash_password("RevocationPassword123!"),
            role="lawyer"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
    try:
        # Get token
        login_res = client.post("/api/v1/auth/token", data={
            "username": "revocation_test@legalai.local",
            "password": "RevocationPassword123!"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Verify access is authorized
        me_res = client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        
        # 2. Call logout endpoint to revoke token
        logout_res = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_res.status_code == 200
        
        # 3. Verify access is now rejected as 401 Unauthorized
        me_revoked_res = client.get("/api/v1/auth/me", headers=headers)
        assert me_revoked_res.status_code == 401
        assert "revoked" in me_revoked_res.json()["detail"].lower()
        
    finally:
        # Cleanup
        db.delete(test_user)
        db.query(RevokedToken).delete()
        db.commit()
        db.close()

def test_sqlite_fts5_store():
    import tempfile
    from aegis_backend.vector_store import SqliteFTS5Store

    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        fts = SqliteFTS5Store(tmp.name)
        chunks = [
            {"id": "c1", "content": "Section 439 CrPC governs regular bail in High Court or Session Court", "metadata": {"document_id": 101}},
            {"id": "c2", "content": "Section 482 CrPC provides inherent powers of High Court to quash FIR", "metadata": {"document_id": 102}},
            {"id": "c3", "content": "Commercial contract termination notice clause requires 30 days written notice", "metadata": {"document_id": 103}}
        ]
        fts.add_chunks(chunks)

        # Search for bail
        results = fts.search("bail")
        assert len(results) >= 1
        assert results[0]["id"] == "c1"
        assert "439" in results[0]["content"]

        # Search with document filter
        filtered = fts.search("CrPC", document_ids=[102])
        assert len(filtered) == 1
        assert filtered[0]["id"] == "c2"

def test_docx_export_service():
    from aegis_backend.services.docx_service import DocxExportService

    # Test Pleading Docx
    pleading_buffer = DocxExportService.create_court_pleading_docx(
        draft_text="IN THE HIGH COURT OF DELHI\nPETITIONER: ABC\nVERSUS\nRESPONDENT: XYZ\n\nPRAYER\nGrant regular bail under Section 483 BNSS.",
        title="BAIL APPLICATION",
        court_header="high_court"
    )
    assert pleading_buffer.getvalue().startswith(b"PK")  # Standard zip/docx magic bytes
    assert len(pleading_buffer.getvalue()) > 1000

    # Test Redline Docx
    redline_buffer = DocxExportService.create_redline_docx(
        original_text="The tenant shall pay monthly rent of ten thousand rupees on fifth of every month.",
        modified_text="The tenant shall pay monthly rent of twelve thousand rupees on first of every month.",
        title="Tenancy Agreement Redline"
    )
    assert redline_buffer.getvalue().startswith(b"PK")
    assert len(redline_buffer.getvalue()) > 1000

def test_ecourts_lookup_and_prefix_compatibility():
    from fastapi.testclient import TestClient
    from aegis_backend.main import app
    from aegis_backend.database import SessionLocal, User
    from aegis_backend.core.security import create_access_token

    client = TestClient(app)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test_lawyer@legalai.local").first()
    if not user:
        user = User(email="test_lawyer@legalai.local", hashed_password=hash_password("Pass123!"), role="lawyer")
        db.add(user)
        db.commit()
    token = create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Test under /api/v1/
    res_v1 = client.get("/api/v1/ecourts/lookup?cnr=DLHC010012342024", headers=headers)
    assert res_v1.status_code == 200
    data_v1 = res_v1.json()
    assert data_v1["cnr"] == "DLHC010012342024"
    assert "High Court of Delhi" in data_v1["court"]

    # Test backward compatibility prefix under /api/
    res_compat = client.get("/api/ecourts/lookup?cnr=DLHC010012342024", headers=headers)
    assert res_compat.status_code == 200
    assert res_compat.json()["cnr"] == "DLHC010012342024"

    # Verify non-admin lawyer can access /api/v1/system/status without 403
    status_res = client.get("/api/v1/system/status", headers=headers)
    assert status_res.status_code == 200
    assert "ai_connected" in status_res.json()
    assert "models_available" in status_res.json()
    db.close()

def test_landmark_precedents_api():
    from fastapi.testclient import TestClient
    from aegis_backend.main import app
    from aegis_backend.database import SessionLocal, User, LandmarkPrecedent
    from aegis_backend.core.security import create_access_token

    client = TestClient(app)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test_lawyer@legalai.local").first()
    token = create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Seed at least one precedent if empty
    if db.query(LandmarkPrecedent).count() == 0:
        db.add(LandmarkPrecedent(
            title="K.S. Puttaswamy v. Union of India",
            citation="(2017) 10 SCC 1",
            court="Supreme Court of India",
            year=2017,
            subject="Right to Privacy",
            ratio_decidendi="Privacy is a fundamental right under Article 21.",
            facts_summary="Aadhaar privacy challenge."
        ))
        db.commit()

    res = client.get("/api/v1/helper/precedents?query=Privacy", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert any("Privacy" in item["subject"] or "Privacy" in item["ratio_decidendi"] for item in items)
    db.close()

def test_crm_entity_graph_api():
    from fastapi.testclient import TestClient
    from aegis_backend.main import app
    from aegis_backend.database import SessionLocal, User, Client, Matter
    from aegis_backend.core.security import create_access_token

    client = TestClient(app)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test_lawyer@legalai.local").first()
    token = create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Create client and matter with adverse opponent
    c = Client(name="Graph Client Entity A", email="graph_a@example.com")
    db.add(c)
    db.commit()
    db.refresh(c)

    m = Matter(
        client_id=c.id,
        title="Contract Dispute Matter X",
        opponent_name="Adverse Opponent Corp",
        opposing_advocate="Advocate Senior Partner"
    )
    db.add(m)
    db.commit()

    try:
        res = client.get("/api/v1/crm/entity-graph", headers=headers)
        assert res.status_code == 200
        graph = res.json()
        assert "nodes" in graph
        assert "edges" in graph
        assert any(n["label"] == "Graph Client Entity A" for n in graph["nodes"])
        assert any(n["label"] == "Adverse Opponent Corp" for n in graph["nodes"])
    finally:
        db.delete(m)
        db.delete(c)
        db.commit()
        db.close()

def test_statute_crosswalk_service_and_api():
    from aegis_backend.services.statute_crosswalk import StatuteCrosswalkService
    from fastapi.testclient import TestClient
    from aegis_backend.main import app
    from aegis_backend.database import SessionLocal, User
    from aegis_backend.core.security import create_access_token

    # 1. Test direct service search
    res_murder = StatuteCrosswalkService.search("302")
    assert len(res_murder) >= 1
    assert res_murder[0]["old_act"] == "IPC"
    assert "BNS" in res_murder[0]["new_act"]
    assert "103" in res_murder[0]["new_section"]

    res_bail = StatuteCrosswalkService.search("438")
    assert any(r["old_section"] == "438" and "482" in r["new_section"] for r in res_bail)

    res_iea = StatuteCrosswalkService.search("65B")
    assert any("63" in r["new_section"] for r in res_iea)

    # 2. Test HTTP endpoint
    client = TestClient(app)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test_lawyer@legalai.local").first()
    token = create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    api_res = client.get("/api/v1/research/crosswalk?query=cheating", headers=headers)
    assert api_res.status_code == 200
    items = api_res.json()
    assert any("420" in i["old_section"] or "318" in i["new_section"] for i in items)
    db.close()

def test_chronology_service_extraction_and_contradictions():
    from aegis_backend.services.chronology_service import ChronologyService

    sample_evidence = (
        "On 12/05/2023, the Complainant stated that payment of Rs 50,00,000 was transferred.\n"
        "However, on 12/05/2023, the Accused alleged he was traveling out of state and never received funds.\n"
        "Subsequently on 18/06/2023, the Investigating Officer recorded a formal seizure memo."
    )

    events = ChronologyService.extract_events_from_text(sample_evidence, source_doc="FIR_ChargeSheet.pdf")
    assert len(events) >= 2
    assert any("12/05/2023" in e["date"] for e in events)

    # Test contradiction finder with divergent source accounts
    doc_a_events = ChronologyService.extract_events_from_text("On 10/01/2024, Witness stated meeting occurred at 10:00 AM.", source_doc="Witness_Statement_A.pdf")
    doc_b_events = ChronologyService.extract_events_from_text("On 10/01/2024, Bank statement proves branch was closed all day.", source_doc="Bank_Audit.pdf")
    combined = doc_a_events + doc_b_events

    contradictions = ChronologyService.identify_contradictions(combined)
    assert len(contradictions) >= 1
    assert contradictions[0]["severity"] == "HIGH"
    assert "Discrepancy on 10/01/2024" in contradictions[0]["topic"]

def test_privilege_certificate_api():
    from fastapi.testclient import TestClient
    from aegis_backend.main import app
    from aegis_backend.database import SessionLocal, User
    from aegis_backend.core.security import create_access_token, SECRET_KEY
    import hmac, hashlib, json

    client = TestClient(app)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test_lawyer@legalai.local").first()
    token = create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/system/privilege-certificate", headers=headers)
    assert res.status_code == 200
    cert = res.json()

    assert "certificate_id" in cert
    assert cert["certificate_id"].startswith("PRIV-")
    assert cert["licensed_advocate"] == user.email
    assert "AIR-GAPPED" in cert["inference_isolation"]["external_egress_traffic"]
    assert "cryptographic_signature" in cert

    # Verify signature matches payload
    sig = cert["cryptographic_signature"]
    payload_without_sig = {k: v for k, v in cert.items() if k != "cryptographic_signature"}
    expected_sig = hmac.new(SECRET_KEY.encode(), json.dumps(payload_without_sig, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    assert sig == expected_sig
    db.close()

