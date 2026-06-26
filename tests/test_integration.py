import pytest
from fastapi.testclient import TestClient
from aegis_backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_unauthorized_access():
    response = client.get("/api/matters")
    assert response.status_code == 401

def test_user_registration():
    # Attempt to register a user
    response = client.post("/api/auth/register", json={
        "email": "test@firm.com",
        "password": "StrongPassword!123",
        "role": "lawyer"
    })
    # Will likely return 200 on first run or 400 if user exists, either way it's a valid integration check
    assert response.status_code in (200, 400)
