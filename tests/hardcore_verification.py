#!/usr/bin/env python3
import sys
import os
import httpx
import json
import time

API_BASE = "http://localhost:8000"

def log_test(name, passed, details=""):
    status = "🟢 PASSED" if passed else "🔴 FAILED"
    print(f"[{status}] {name}")
    if details:
        print(f"   Detail: {details}")
    print("-" * 60)

def run_hardcore_tests():
    print("=" * 60)
    print("⚖️ STARTING AEGISAI HARDCORE BACKEND INTEGRATION TEST SUITE")
    print("=" * 60)
    
    # Check server availability
    try:
        httpx.get(f"{API_BASE}/api/system/status", timeout=2.0)
    except Exception:
        print(f"🔴 ERROR: Backend server is not running on {API_BASE}.")
        print("Please start the backend before running the tests:")
        print("   PYTHONPATH=. ./venv/bin/python aegis_backend/main.py")
        sys.exit(1)

    client = httpx.Client(base_url=API_BASE, timeout=30.0)
    token = None
    headers = {}

    # Test 1: User Registration
    test_email = f"test_advocate_{int(time.time())}@firm.com"
    test_password = "SecurePassword123!"
    try:
        res = client.post("/api/auth/register", json={
            "email": test_email,
            "password": test_password,
            "role": "lawyer"
        })
        passed = res.status_code == 200
        details = f"Registered User: {test_email}" if passed else f"Status {res.status_code}: {res.text}"
        log_test("Auth - User Registration", passed, details)
    except Exception as e:
        log_test("Auth - User Registration", False, str(e))
        sys.exit(1)

    # Test 2: Login / Token Retrieve
    try:
        res = client.post("/api/auth/token", data={
            "username": test_email,
            "password": test_password
        })
        passed = res.status_code == 200
        if passed:
            token = res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            details = f"Token obtained successfully"
        else:
            details = f"Status {res.status_code}: {res.text}"
        log_test("Auth - Login token generation", passed, details)
    except Exception as e:
        log_test("Auth - Login token generation", False, str(e))
        sys.exit(1)

    # Test 3: Get Profile Profile Info (Auth Me)
    try:
        res = client.get("/api/auth/me", headers=headers)
        passed = res.status_code == 200 and res.json()["email"] == test_email
        details = f"Fetched email match: {res.json().get('email')}" if passed else res.text
        log_test("Auth - Get profile (/api/auth/me)", passed, details)
    except Exception as e:
        log_test("Auth - Get profile", False, str(e))

    # Test 4: Configure Custom Firm Settings (Letterhead & Logo)
    mock_logo_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9sJEw0tKnGJF4UAAAAIdEVYdENvbW1lbnQA9syWvwAAADFJREFUGFdj/P//PwM2wMRACQhGKgApRoqBipFiwKqYKAbqY6IYMKMmksFIMmBGTSQDAOzZBgv54H68AAAAAElFTkSuQmCC"
    try:
        res = client.post("/api/user/firm-settings", headers=headers, json={
            "firm_name": "Chambers of Supreme Advocate",
            "firm_logo": mock_logo_b64
        })
        passed = res.status_code == 200
        details = res.json().get("message") if passed else res.text
        log_test("Settings - Custom Firm Config", passed, details)
    except Exception as e:
        log_test("Settings - Custom Firm Config", False, str(e))

    # Test 5: Verify settings persisted on /auth/me
    try:
        res = client.get("/api/auth/me", headers=headers)
        data = res.json()
        passed = data.get("firm_name") == "Chambers of Supreme Advocate" and data.get("firm_logo") == mock_logo_b64
        details = f"Persisted Name: {data.get('firm_name')}" if passed else "Data mismatch on settings verify"
        log_test("Settings - Verification check", passed, details)
    except Exception as e:
        log_test("Settings - Verification check", False, str(e))

    # Test 6: 2FA Status check
    try:
        res = client.get("/api/2fa/status", headers=headers)
        passed = res.status_code == 200 and res.json()["enabled"] is False
        details = f"Enabled state: {res.json().get('enabled')}" if passed else res.text
        log_test("MFA - 2FA check (Default Disabled)", passed, details)
    except Exception as e:
        log_test("MFA - 2FA check", False, str(e))

    # Test 7: 2FA Setup generation
    try:
        res = client.post("/api/2fa/setup", headers=headers)
        passed = res.status_code == 200 and "secret" in res.json() and "qr_code_base64" in res.json()
        details = f"TOTP Secret Generated: {res.json().get('secret')[:8]}..." if passed else f"Status {res.status_code}: {res.text}"
        log_test("MFA - 2FA Secret setup generation", passed, details)
    except Exception as e:
        log_test("MFA - 2FA Secret setup generation", False, str(e))

    # Test 8: Client CRM Creation
    client_id = None
    try:
        res = client.post("/api/clients", headers=headers, json={
            "name": "Reliance Corporate Industries",
            "email": "legal@reliance.com",
            "phone": "+91-9876543210",
            "notes": "Premium corporate counsel client."
        })
        passed = res.status_code == 200 and "id" in res.json()
        if passed:
            client_id = res.json()["id"]
            details = f"Created Client ID: {client_id}"
        else:
            details = f"Status {res.status_code}: {res.text}"
        log_test("CRM - Client creation", passed, details)
    except Exception as e:
        log_test("CRM - Client creation", False, str(e))

    # Test 9: Matter Creation with CNR Number
    matter_id = None
    test_cnr = "DLHC010005552026"
    try:
        res = client.post("/api/matters", headers=headers, json={
            "client_id": client_id,
            "title": "Reliance Patents Infringement Litigation",
            "case_number": "WP-1254/2026",
            "cnr_number": test_cnr,
            "court": "High Court of Delhi",
            "judge": "Hon'ble Judge Roy",
            "opponent_name": "Generic Infra Ltd",
            "opposing_advocate": "V. K. Singh, Adv.",
            "status": "open",
            "facts": "Patent litigation regarding proprietary communication channels."
        })
        passed = res.status_code == 200
        if passed:
            matter_id = res.json()["id"]
            details = f"Created Matter ID: {matter_id} with CNR: {res.json().get('cnr_number')}"
        else:
            details = res.text
        log_test("Matters - Case creation with CNR", passed, details)
    except Exception as e:
        log_test("Matters - Case creation with CNR", False, str(e))

    # Test 10: eCourts CNR Sync and Lock Verification
    try:
        res = client.post(f"/api/matters/{matter_id}/sync-ecourts", headers=headers)
        passed = res.status_code == 200 and "status" in res.json()
        if passed:
            data = res.json()
            details = f"Fetched Court: {data.get('court')} | Judge: {data.get('judge')} | Hearing: {data.get('hearing_date')}"
        else:
            details = res.text
        log_test("eCourts - Sync online date and status", passed, details)
    except Exception as e:
        log_test("eCourts - Sync online date and status", False, str(e))

    # Test 11: eCourts Lock Check (Verifying that subsequent calls block modification)
    try:
        res = client.post(f"/api/matters/{matter_id}/sync-ecourts", headers=headers)
        passed = res.status_code == 200 and res.json().get("status") == "locked"
        details = res.json().get("message") if passed else res.text
        log_test("eCourts - Data lock verification", passed, details)
    except Exception as e:
        log_test("eCourts - Data lock verification", False, str(e))

    # Test 12: Billing Time Logging
    entry_id = None
    try:
        res = client.post("/api/billing/time-entry", headers=headers, json={
            "matter_id": matter_id,
            "description": "Drafted patent arguments and analyzed opponent statement",
            "hours": "2.5",
            "rate_per_hour": "10000",
            "date": "2026-05-31"
        })
        passed = res.status_code == 200
        if passed:
            entry_id = res.json()["id"]
            details = f"Logged 2.5 hours at ₹10,000/hr. Entry ID: {entry_id}"
        else:
            details = res.text
        log_test("Billing - Time Entry Log", passed, details)
    except Exception as e:
        log_test("Billing - Time Entry Log", False, str(e))

    # Test 13: Invoice Generation with GST Calculation Check
    try:
        res = client.post("/api/billing/invoice", headers=headers, json={
            "client_id": client_id,
            "matter_id": matter_id,
            "notes": "Litigation drafting services."
        })
        passed = res.status_code == 200
        if passed:
            data = res.json()
            # 2.5h * 10,000 = 25,000 base amount. 18% GST = 4,500. Grand total = 29,500.
            gst_correct = float(data["gst_amount"]) == 4500.0
            grand_correct = float(data["grand_total"]) == 29500.0
            passed = gst_correct and grand_correct
            details = f"Inv: {data['invoice_number']} | Base: ₹{data['total_amount']} | 18% GST: ₹{data['gst_amount']} | Total: ₹{data['grand_total']}"
        else:
            details = res.text
        log_test("Billing - GST Invoice Generator", passed, details)
    except Exception as e:
        log_test("Billing - GST Invoice Generator", False, str(e))

    # Test 14: Analytics Summary Endpoint
    try:
        res = client.get("/api/analytics/summary", headers=headers)
        passed = res.status_code == 200 and "total_matters" in res.json()
        if passed:
            data = res.json()
            details = f"Total Cases: {data.get('total_matters')} | Total Revenue logged: ₹{data.get('total_revenue_inr')}"
        else:
            details = res.text
        log_test("Analytics - Metrics retrieval", passed, details)
    except Exception as e:
        log_test("Analytics - Metrics retrieval", False, str(e))

    # Test 15: Clean Up Client & Matter
    try:
        res = client.delete(f"/api/clients/{client_id}", headers=headers)
        passed = res.status_code == 200
        details = "Client and cascaded matter deleted successfully" if passed else res.text
        log_test("Cleanup - Cascade remove testing assets", passed, details)
    except Exception as e:
        log_test("Cleanup - Cascade remove testing assets", False, str(e))

    print("=" * 60)
    print("⚖️ VERIFICATION RUN COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_hardcore_tests()
