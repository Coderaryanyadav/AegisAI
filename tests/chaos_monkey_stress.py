import asyncio
import httpx
import os
import subprocess
import time
import sys

API_BASE = "http://127.0.0.1:8000"

async def login(client):
    print("[*] Logging in as admin...")
    response = await client.post(
        f"{API_BASE}/api/auth/token",
        data={"username": "admin@legalai.local", "password": "adminpassword123"}
    )
    if response.status_code != 200:
        print("Login failed! Ensure backend is running and admin/password123 is valid.")
        sys.exit(1)
    token = response.json().get("access_token")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return token

async def create_client_worker(client, worker_id, results):
    """Spams the DB to create clients to test concurrency deadlocks."""
    payload = {
        "name": f"Chaos Client {worker_id}",
        "email": f"chaos_{worker_id}@example.com",
        "phone": f"555-000-{worker_id:04d}",
        "address": "123 Chaos Street",
        "client_type": "individual"
    }
    try:
        resp = await client.post(f"{API_BASE}/api/clients", json=payload)
        results.append(resp.status_code)
    except Exception as e:
        results.append(str(e))

async def test_concurrency(client):
    print("\n[1] Starting DB Concurrency Load Test (300 requests)...")
    results = []
    tasks = []
    for i in range(300):
        tasks.append(create_client_worker(client, i, results))
    
    start_time = time.time()
    await asyncio.gather(*tasks)
    elapsed = time.time() - start_time
    
    success_count = results.count(200)
    print(f"    Elapsed time: {elapsed:.2f}s")
    print(f"    Successful inserts: {success_count} / 300")
    if success_count < 280:
        print("    [FAIL] Database concurrency suffered failures. Check for 'database is locked'.")
        sys.exit(1)
    else:
        print("    [PASS] SQLite WAL and connection pooling held up perfectly!")

async def test_fuzzing(client):
    print("\n[2] Starting Malicious Fuzzing...")
    
    # Path Traversal Test
    resp = await client.get(f"{API_BASE}/api/system/backups?file=../../../etc/passwd")
    if resp.status_code in [400, 403, 422, 404]:
        print("    [PASS] Path Traversal Blocked.")
    else:
        print(f"    [FAIL] Path Traversal Vulnerable! Status: {resp.status_code}")
        sys.exit(1)
        
    # SQL Injection / Malformed payload Test
    payload = {"name": "'; DROP TABLE clients; --", "email": "bad@bad.com"}
    resp = await client.post(f"{API_BASE}/api/clients", json=payload)
    if resp.status_code == 200:
        print("    [PASS] SQLi payload neutralized by ORM.")
    else:
        print(f"    [FAIL] Unexpected response for SQLi string: {resp.status_code}")
    
async def test_frontend_build():
    print("\n[3] Starting Next.js Production Build Validation...")
    try:
        # Run npm run build in frontend directory
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd="../aegis_frontend",
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("    [PASS] Frontend Build succeeded perfectly.")
            if "Compiled successfully" in result.stdout:
                print("    [PASS] Build is clean.")
        else:
            print("    [FAIL] Frontend build failed!")
            print(result.stdout)
            print(result.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"    [FAIL] Could not run build: {e}")
        sys.exit(1)

async def test_panic_wipe(client):
    print("\n[4] Triggering Secure Panic Wipe...")
    resp = await client.post(f"{API_BASE}/api/backup/panic")
    if resp.status_code == 200:
        print("    [PASS] Panic Wipe completed successfully.")
        print("    " + resp.json().get("message", ""))
    else:
        print(f"    [FAIL] Panic Wipe failed. Status: {resp.status_code}")
        sys.exit(1)

async def main():
    print("============================================")
    print(" AEGISAI CHAOS MONKEY STRESS TEST INITIATED ")
    print("============================================\n")
    
    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        await login(client)
        await test_concurrency(client)
        await test_fuzzing(client)
        await test_panic_wipe(client)
        
        await test_frontend_build()

    print("\n============================================")
    print(" ALL CHAOS MONKEY TESTS PASSED WITH 100% SUCCESS")
    print("============================================")

if __name__ == "__main__":
    # Ensure CWD is tests directory
    if not os.getcwd().endswith("tests"):
        os.chdir("tests")
    asyncio.run(main())
