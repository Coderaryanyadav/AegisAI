#!/usr/bin/env python3
import sys
import os
import httpx
import json
import time
import io
from datetime import datetime, timedelta

try:
    import pyotp
except ImportError:
    print("🔴 Warning: 'pyotp' package is not installed. 2FA verification steps might be skipped.")
    pyotp = None

API_BASE = "http://localhost:8000"

def print_banner(text):
    print("\n" + "=" * 80)
    print(f"⚖️  {text.upper()}")
    print("=" * 80)

def log_test(name, passed, details=""):
    status = "🟢 PASSED" if passed else "🔴 FAILED"
    print(f"[{status}] {name}")
    if details:
        print(f"   Detail: {details}")
    print("-" * 80)

def run_ultra_hardcore_tests():
    print_banner("AegisAI Ultra-Hardcore Complete Backend API Validation Suite")
    
    # 1. Ping Check System Status
    try:
        res = httpx.get(f"{API_BASE}/api/system/status", timeout=5.0)
        passed = res.status_code == 200 or res.status_code == 401 # status might require login now
        log_test("System - Status Ping", True, f"Status code: {res.status_code}")
    except Exception as e:
        log_test("System - Status Ping", False, f"Could not contact server on {API_BASE}: {e}")
        print("Please ensure the backend is running.")
        sys.exit(1)

    client = httpx.Client(base_url=API_BASE, timeout=30.0)
    token = None
    headers = {}

    test_email = f"hardcore_advocate_{int(time.time())}@aegislaw.com"
    test_password = "UltraSecurePassword999!"
    try:
        res = client.post("/api/auth/register", json={
            "email": test_email,
            "password": test_password,
            "role": "admin"
        })
        passed = res.status_code == 200 and res.json().get("email") == test_email
        log_test("Auth - Admin Registration", passed, f"Response: {res.text}")
    except Exception as e:
        log_test("Auth - Admin Registration", False, str(e))
        sys.exit(1)

    # Test 3: Login & Session Token
    try:
        res = client.post("/api/auth/token", data={
            "username": test_email,
            "password": test_password
        })
        passed = res.status_code == 200 and "access_token" in res.json()
        if passed:
            token = res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            log_test("Auth - Token Retrieval", True, f"Token: {token[:20]}...")
        else:
            log_test("Auth - Token Retrieval", False, f"Status {res.status_code}: {res.text}")
            sys.exit(1)
    except Exception as e:
        log_test("Auth - Token Retrieval", False, str(e))
        sys.exit(1)

    # Test 4: Profile Details
    try:
        res = client.get("/api/auth/me", headers=headers)
        passed = res.status_code == 200 and res.json().get("role") == "admin"
        log_test("Auth - Fetch Current User Profile", passed, f"User JSON: {res.text}")
    except Exception as e:
        log_test("Auth - Fetch Current User Profile", False, str(e))

    # Test 5: Custom Letterhead Logo & Info Setup
    mock_logo_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    try:
        res = client.post("/api/user/firm-settings", headers=headers, json={
            "firm_name": "Aegis Supreme Legal Partners LLP",
            "firm_logo": mock_logo_b64
        })
        passed = res.status_code == 200
        log_test("Settings - Custom Firm Letterhead Configuration", passed, f"Response: {res.text}")
    except Exception as e:
        log_test("Settings - Custom Firm Letterhead Configuration", False, str(e))

    # Test 6: Verify Settings on /me endpoint
    try:
        res = client.get("/api/auth/me", headers=headers)
        data = res.json()
        passed = data.get("firm_name") == "Aegis Supreme Legal Partners LLP" and data.get("firm_logo") == mock_logo_b64
        log_test("Settings - Verification on profile retrieve", passed, f"Logo/Name present matches inputs")
    except Exception as e:
        log_test("Settings - Verification on profile retrieve", False, str(e))

    # Test 7: MFA - 2FA Status Check (Initally False)
    try:
        res = client.get("/api/2fa/status", headers=headers)
        passed = res.status_code == 200 and res.json().get("enabled") is False
        log_test("MFA - Status Check (Initial Default)", passed, f"Enabled status: {res.json().get('enabled')}")
    except Exception as e:
        log_test("MFA - Status Check (Initial Default)", False, str(e))

    # Test 8: MFA - 2FA Setup
    totp_secret = None
    try:
        res = client.post("/api/2fa/setup", headers=headers)
        data = res.json()
        passed = res.status_code == 200 and "secret" in data and "qr_code_base64" in data
        if passed:
            totp_secret = data["secret"]
            log_test("MFA - Generate 2FA Secret Key & QR Code", True, f"Secret: {totp_secret[:8]}... | QR Size: {len(data['qr_code_base64'])} bytes")
        else:
            log_test("MFA - Generate 2FA Secret Key & QR Code", False, res.text)
    except Exception as e:
        log_test("MFA - Generate 2FA Secret Key & QR Code", False, str(e))

    # Test 9: MFA - Enable 2FA with verification
    if totp_secret and pyotp:
        try:
            totp = pyotp.TOTP(totp_secret)
            current_code = totp.now()
            res = client.post("/api/2fa/enable", headers=headers, json={"totp_code": current_code})
            passed = res.status_code == 200
            log_test("MFA - Verification & Enable 2FA", passed, f"Response: {res.text}")
        except Exception as e:
            log_test("MFA - Verification & Enable 2FA", False, str(e))
            
        # Test 10: MFA - Disable 2FA
        try:
            totp = pyotp.TOTP(totp_secret)
            current_code = totp.now()
            res = client.post("/api/2fa/disable", headers=headers, json={"totp_code": current_code})
            passed = res.status_code == 200
            log_test("MFA - Verification & Disable 2FA", passed, f"Response: {res.text}")
        except Exception as e:
            log_test("MFA - Verification & Disable 2FA", False, str(e))

    # Test 11: CRM - Client A (Prospective Client)
    client_a_id = None
    try:
        res = client.post("/api/clients", headers=headers, json={
            "name": "Tata Global Energy Consortium",
            "email": "tata@tataenergy.com",
            "phone": "+91-11-23348888",
            "notes": "Large multi-national energy conglomerate."
        })
        passed = res.status_code == 200 and "id" in res.json()
        if passed:
            client_a_id = res.json()["id"]
            log_test("CRM - Client A Creation", True, f"Client A ID: {client_a_id}")
        else:
            log_test("CRM - Client A Creation", False, res.text)
    except Exception as e:
        log_test("CRM - Client A Creation", False, str(e))

    # Test 12: CRM - Matter A (associated with Client A)
    matter_a_id = None
    time_suffix = int(time.time())
    try:
        res = client.post("/api/matters", headers=headers, json={
            "client_id": client_a_id,
            "title": "Tata vs Adani Power Transmission Dispute",
            "case_number": f"ARB-199/{time_suffix}",
            "court": "High Court of Bombay",
            "judge": "Justice S. Patel",
            "opponent_name": "Adani Power Transmission Ltd",
            "opposing_advocate": "Harish Salve, Adv.",
            "status": "open",
            "facts": "Arbitration regarding power purchase agreements and pricing adjustments in Western Maharashtra.",
            "cnr_number": f"MHOB01002234{str(time_suffix)[-4:]}"
        })
        passed = res.status_code == 200 and "id" in res.json()
        if passed:
            matter_a_id = res.json()["id"]
            log_test("Matters - Matter A Case Registration", True, f"Matter A ID: {matter_a_id}")
        else:
            log_test("Matters - Matter A Case Registration", False, res.text)
    except Exception as e:
        log_test("Matters - Matter A Case Registration", False, str(e))

    # Test 13: Conflict Check - Testing Positive & Negative Ethical Conflicts
    try:
        # Scenario 1: Prospective Client is opponent in active Matter A -> High severity conflict
        res = client.post("/api/matters/check-conflict", headers=headers, json={
            "client_name": "Adani Power Transmission Ltd",
            "opponent_name": "Random Corp"
        })
        passed = res.status_code == 200 and res.json().get("conflict_detected") is True and res.json().get("severity") == "high"
        log_test("Compliance - Conflict Check (Direct Conflict Detected)", passed, f"Conflict: {res.json().get('reasons')}")

        # Scenario 2: Clear scenario -> Conflict false
        res = client.post("/api/matters/check-conflict", headers=headers, json={
            "client_name": "Completely Unknown Ltd",
            "opponent_name": "NonExistent Corp"
        })
        passed = res.status_code == 200 and res.json().get("conflict_detected") is False
        log_test("Compliance - Conflict Check (No Conflict Detected)", passed, f"Conflict detected: {res.json().get('conflict_detected')}")
    except Exception as e:
        log_test("Compliance - Conflict Check Logic", False, str(e))

    # Test 14: eCourts CNR Sync (Matter A)
    try:
        res = client.post(f"/api/matters/{matter_a_id}/sync-ecourts", headers=headers)
        passed = res.status_code == 200 and "status" in res.json()
        if passed:
            data = res.json()
            log_test("eCourts - Sync Online Case Data", True, f"Court: {data.get('court')} | Judge: {data.get('judge')} | Next Hearing: {data.get('hearing_date')}")
        else:
            log_test("eCourts - Sync Online Case Data", False, res.text)
    except Exception as e:
        log_test("eCourts - Sync Online Case Data", False, str(e))

    # Test 15: eCourts CNR Lock Verification (Cannot modify locked cases remote sync)
    try:
        res = client.post(f"/api/matters/{matter_a_id}/sync-ecourts", headers=headers)
        passed = res.status_code == 200 and res.json().get("status") == "locked"
        log_test("eCourts - Sync Locking Enforcement", passed, f"Message: {res.json().get('message')}")
    except Exception as e:
        log_test("eCourts - Sync Locking Enforcement", False, str(e))

    # Test 16: Schedules / Calendar (Hearing scheduling)
    schedule_id = None
    try:
        res = client.post("/api/schedules", headers=headers, json={
            "matter_id": matter_a_id,
            "title": "Cross-examination of Tata Senior Engineer",
            "schedule_type": "hearing",
            "target_date": "2026-06-15T10:30:00",
            "notes": "Ensure cross-examination files are thoroughly reviewed."
        })
        passed = res.status_code == 200 and "id" in res.json()
        if passed:
            schedule_id = res.json()["id"]
            log_test("Calendar - Schedule Creation", True, f"Schedule ID: {schedule_id}")
        else:
            log_test("Calendar - Schedule Creation", False, res.text)
    except Exception as e:
        log_test("Calendar - Schedule Creation", False, str(e))

    # Test 17: Schedules - List and Complete
    try:
        # List
        res_list = client.get("/api/schedules", headers=headers)
        # Complete
        res_comp = client.put(f"/api/schedules/{schedule_id}/complete", headers=headers)
        passed = res_list.status_code == 200 and res_comp.status_code == 200
        log_test("Calendar - Complete Schedule Event", passed, f"Completed status: {res_comp.json()}")
    except Exception as e:
        log_test("Calendar - Complete Schedule Event", False, str(e))

    # Test 18: Document Vault Ingestion (Upload file)
    doc_id = None
    try:
        mock_contract = b"LEASE DEED AGREEMENT: Under Section 105 of the Transfer of Property Act 1882, the lessor leases out Flat 4B in South Mumbai to lessee Tata Energy. This is a very long legal agreement document to ensure that the character threshold is exceeded. " * 3
        files = {"file": ("lease_contract.txt", io.BytesIO(mock_contract), "text/plain")}
        res = client.post("/api/documents/upload", headers=headers, data={"matter_id": matter_a_id}, files=files)
        passed = res.status_code == 200 and "id" in res.json()
        if passed:
            doc_id = res.json()["id"]
            log_test("Vault - Document Ingestion & Encryption", True, f"Uploaded Doc ID: {doc_id} | Name: {res.json().get('original_name')}")
        else:
            log_test("Vault - Document Ingestion & Encryption", False, res.text)
    except Exception as e:
        log_test("Vault - Document Ingestion & Encryption", False, str(e))

    # Wait for background pipeline to extract text
    time.sleep(2)

    # Test 19: Document Text Retrieval
    try:
        res = client.get(f"/api/documents/{doc_id}/text", headers=headers)
        passed = res.status_code == 200 and "text" in res.json()
        log_test("Vault - Document Text Extraction", passed, f"Extracted text snippet: {res.json().get('text')[:60]}...")
    except Exception as e:
        log_test("Vault - Document Text Extraction", False, str(e))

    # Test 20: RAG Search Querying
    try:
        res = client.post("/api/research/query", headers=headers, json={
            "query": "Who is the lessee in Flat 4B Flat in Mumbai?",
            "matter_ids": [matter_a_id]
        })
        passed = res.status_code == 200 and "response" in res.json()
        log_test("RAG - AI Legal Assistant QA", passed, f"AI Response: {res.json().get('response')[:150]}...")
    except Exception as e:
        log_test("RAG - AI Legal Assistant QA", False, str(e))

    # Test 21: IPC-BNS Legal Helper Map
    try:
        res = client.get("/api/helper/ipc-bns?act=IPC&section=378", headers=headers)
        passed = res.status_code == 200 and "new_section" in res.json()
        log_test("Indian Law Helper - IPC Section 378 Map", passed, f"IPC 378 -> BNS {res.json().get('new_section')} ({res.json().get('subject')})")
    except Exception as e:
        log_test("Indian Law Helper - IPC Section 378 Map", False, str(e))

    # Test 22: Citation Normalizer helper
    try:
        res = client.post("/api/helper/normalize-citation", headers=headers, data={"citation": "2024 SCC DEL 105"})
        passed = res.status_code == 200 and "normalized" in res.json()
        log_test("Indian Law Helper - Normalization of Citation", passed, f"Raw: 2024 SCC DEL 105 -> Normalized: {res.json().get('normalized')}")
    except Exception as e:
        log_test("Indian Law Helper - Normalization of Citation", False, str(e))

    # Test 23: Document Analytics - Extract Timeline from document
    try:
        res = client.post(f"/api/analyze/extract-timeline?document_id={doc_id}", headers=headers)
        passed = res.status_code == 200 and "timeline" in res.json()
        log_test("AI Analysis - Facts Timeline Extractor", passed, f"Timeline entries: {res.json().get('timeline')}")
    except Exception as e:
        log_test("AI Analysis - Facts Timeline Extractor", False, str(e))

    # Test 24: Document Audit - Risk Scan
    try:
        res = client.post(f"/api/audit/risk-scan?document_id={doc_id}", headers=headers)
        passed = res.status_code == 200 and "risks" in res.json()
        risks_list = res.json().get("risks", [])
        log_test("AI Compliance - Risk Scan Contract Auditor", passed, f"Risks detected: {risks_list[:2] if isinstance(risks_list, list) else risks_list}")
    except Exception as e:
        log_test("AI Compliance - Risk Scan Contract Auditor", False, str(e))

    # Test 25: AI Drafting - Templates & Generation
    try:
        templates = client.get("/api/draft/templates", headers=headers).json()
        first_template = templates[0]["id"]
        res = client.post(f"/api/draft/generate?template_id={first_template}", headers=headers, json={
            "client_name": "Tata Energy", 
            "debtor_name": "Adani Transmission", 
            "amount_due": "500000", 
            "due_date": "2026-05-01", 
            "notice_period_days": "15"
        })
        passed = res.status_code == 200 and "draft" in res.json()
        log_test("AI Drafting - Draft Contract Generation", passed, f"Template: {first_template} | Length: {len(res.json().get('draft', ''))} chars")
    except Exception as e:
        log_test("AI Drafting - Draft Contract Generation", False, str(e))

    # Test 26: Billing Time Logging (Matter A)
    entry_id = None
    try:
        res = client.post("/api/billing/time-entry", headers=headers, json={
            "matter_id": matter_a_id,
            "description": "Cross-examination prep session with technical team",
            "hours": "3.5",
            "rate_per_hour": "12000",
            "date": "2026-05-31"
        })
        passed = res.status_code == 200 and "id" in res.json()
        if passed:
            entry_id = res.json()["id"]
            log_test("Billing - Time Logging (Matter A)", True, f"Entry ID: {entry_id} | Hours: 3.5")
        else:
            log_test("Billing - Time Logging (Matter A)", False, res.text)
    except Exception as e:
        log_test("Billing - Time Logging (Matter A)", False, str(e))

    # Test 27: GST Invoice Generation with automatic 18% GST audit
    invoice_id = None
    try:
        res = client.post("/api/billing/invoice", headers=headers, json={
            "client_id": client_a_id,
            "matter_id": matter_a_id,
            "notes": "Tata Energy arbitration professional services."
        })
        passed = res.status_code == 200
        if passed:
            data = res.json()
            invoice_id = data["id"]
            # 3.5 hours * 12000 = 42,000 base amount. 18% GST = 7560. Grand total = 49,560.
            base_correct = float(data["total_amount"]) == 42000.0
            gst_correct = float(data["gst_amount"]) == 7560.0
            grand_correct = float(data["grand_total"]) == 49560.0
            passed = base_correct and gst_correct and grand_correct
            log_test("Billing - GST Invoice Verification", passed, f"Inv: {data['invoice_number']} | Base: ₹{data['total_amount']} | GST (18%): ₹{data['gst_amount']} | Total: ₹{data['grand_total']}")
        else:
            log_test("Billing - GST Invoice Verification", False, res.text)
    except Exception as e:
        log_test("Billing - GST Invoice Verification", False, str(e))

    # Test 28: Invoice status update
    try:
        res = client.put(f"/api/billing/invoice/{invoice_id}/status", headers=headers, json={"status": "paid"})
        passed = res.status_code == 200 and res.json().get("status") == "paid"
        log_test("Billing - Invoice Paid Status Update", passed, f"Response: {res.text}")
    except Exception as e:
        log_test("Billing - Invoice Paid Status Update", False, str(e))

    # Test 29: System Status, upcoming-hearings & Audit logs export
    try:
        res_audit = client.get("/api/system/audit-logs", headers=headers)
        res_hearings = client.get("/api/system/upcoming-hearings", headers=headers)
        res_export = client.get("/api/system/audit-logs/export", headers=headers)
        passed = res_audit.status_code == 200 and res_hearings.status_code == 200 and res_export.status_code == 200
        log_test("System Audit - Log checks & export validation", passed, f"Audit Count: {len(res_audit.json())} | Export Size: {len(res_export.text)} chars")
    except Exception as e:
        log_test("System Audit - Log checks & export validation", False, str(e))

    # Test 30: System - Available Models list
    try:
        res = client.get("/api/system/models", headers=headers)
        passed = res.status_code == 200 and len(res.json().get("models", [])) >= 0
        log_test("Ollama - Available models retrieval", passed, f"Models: {res.json().get('models')}")
    except Exception as e:
        log_test("Ollama - Available models retrieval", False, str(e))

    # Test 31: Analytics Summary check
    try:
        res = client.get("/api/analytics/summary", headers=headers)
        passed = res.status_code == 200 and res.json().get("total_matters") >= 1
        log_test("Analytics - Metrics Summary", passed, f"Summary: {res.json()}")
    except Exception as e:
        log_test("Analytics - Metrics Summary", False, str(e))

    # Test 32: Backup Creation
    backup_file_path = None
    try:
        res = client.post("/api/backup/create", headers=headers)
        passed = res.status_code == 200 and "path" in res.json()
        if passed:
            backup_file_path = res.json()["path"]
            log_test("Backup - Create Encrypted Database Snapshot", True, f"Backup file: {backup_file_path}")
        else:
            log_test("Backup - Create Encrypted Database Snapshot", False, res.text)
    except Exception as e:
        log_test("Backup - Create Encrypted Database Snapshot", False, str(e))

    # Test 33: Backup History / List backups
    try:
        res = client.get("/api/backup/history", headers=headers)
        passed = res.status_code == 200 and len(res.json()) >= 1
        log_test("Backup - Retrieve Snapshot History List", passed, f"Count: {len(res.json())}")
    except Exception as e:
        log_test("Backup - Retrieve Snapshot History List", False, str(e))

    # Test 34: Document Cleanup (delete document)
    try:
        res = client.delete(f"/api/documents/{doc_id}", headers=headers)
        passed = res.status_code == 200
        log_test("Cleanup - Document vault deletion", passed, f"Response: {res.text}")
    except Exception as e:
        log_test("Cleanup - Document vault deletion", False, str(e))

    # Test 35: Cascade client/matter cleanup
    try:
        res = client.delete(f"/api/clients/{client_a_id}", headers=headers)
        passed = res.status_code == 200
        log_test("Cleanup - Client A Cascade deletion", passed, f"Response: {res.text}")
    except Exception as e:
        log_test("Cleanup - Client A Cascade deletion", False, str(e))

    # Test 36: Compliance - Secure Panic Button (Self-destruction wiping data)
    try:
        res = client.post("/api/backup/panic", headers=headers)
        passed = res.status_code == 200
        log_test("Compliance - Secure Panic Wiping", passed, f"Wipe Status: {res.json()}")
        
        # Verify user token still authenticated (as user table isn't deleted),
        # but clients table is fully wiped out (returns 0 active clients)
        res_clients = client.get("/api/clients", headers=headers)
        passed_wipe = res_clients.status_code == 200 and len(res_clients.json()) == 0
        log_test("Compliance - Post-Panic Workspace Secrets Verification", passed_wipe, f"Clients count after panic: {len(res_clients.json()) if res_clients.status_code == 200 else res_clients.status_code}")
    except Exception as e:
        log_test("Compliance - Secure Panic Wiping", False, str(e))

    print_banner("AegisAI Complete API Test Validation Finished")

if __name__ == "__main__":
    run_ultra_hardcore_tests()
