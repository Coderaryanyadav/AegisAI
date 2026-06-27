import os
import sys
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import pytest
from fastapi.testclient import TestClient
from aegis_backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_unauthorized_access():
    response = client.get("/api/v1/matters")
    assert response.status_code == 401

def test_user_registration_and_fuzzing():
    # Attempt to register a user
    response = client.post("/api/v1/auth/register", json={
        "email": "test@firm.com",
        "password": "StrongPassword!123",
        "role": "lawyer"
    })
    assert response.status_code in (200, 400)

def get_admin_token():
    response = client.post("/api/v1/auth/token", data={"username": "admin@legalai.local", "password": "adminpassword123"})
    if response.status_code == 200:
        data = response.json()
        if data.get("must_change_password"):
            client.headers.update({"Authorization": f"Bearer {data['access_token']}"})
            pw_resp = client.post("/api/v1/auth/change-default-password", data={
                "current_password": "adminpassword123",
                "new_password": "StrongPassword123!"
            })
            assert pw_resp.status_code == 200
            # Login again
            response = client.post("/api/v1/auth/token", data={"username": "admin@legalai.local", "password": "StrongPassword123!"})
            return response.json().get("access_token")
        return data.get("access_token")
    
    # Try the new password if already changed
    response = client.post("/api/v1/auth/token", data={"username": "admin@legalai.local", "password": "StrongPassword123!"})
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin login failed, DB might not be seeded or password is unknown.")

def test_security_fuzzing_path_traversal():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Path Traversal
    resp = client.get("/api/v1/system/backups?file=../../../etc/passwd", headers=headers)
    assert resp.status_code in [400, 403, 404, 422], "Path Traversal vulnerability detected!"

def test_security_fuzzing_sql_injection():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # SQLi Payload
    payload = {"name": "'; DROP TABLE clients; --", "email": "bad@bad.com"}
    resp = client.post("/api/v1/clients", json=payload, headers=headers)
    assert resp.status_code in [200, 422], "Unexpected response for SQLi string!"
    
def test_secure_panic_wipe():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = client.post("/api/v1/backup/panic", headers=headers)
    assert resp.status_code == 200
    assert "Active records scrubbed" in resp.json().get("message", "")
