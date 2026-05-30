import requests
import json

API_URL = "http://127.0.0.1:8000"

def test_rag():
    print("[*] Authenticating with backend...")
    payload = {"username": "admin@legalai.local", "password": "adminpassword123"}
    response = requests.post(f"{API_URL}/api/auth/token", data=payload)
    if response.status_code != 200:
        print(f"[!] Authentication failed: {response.text}")
        return
        
    token = response.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("[*] Retrieving documents list...")
    doc_res = requests.get(f"{API_URL}/api/docs", headers=headers)
    if doc_res.status_code != 200:
        print(f"[!] Failed to get docs: {doc_res.text}")
        return
        
    docs = doc_res.json()
    print(f"[*] Indexed documents in database: {docs}")
    if not docs:
        print("[!] No documents to query.")
        return
        
    doc_ids = [d["id"] for d in docs]
    
    # Run a test query
    query = "Who is the petitioner or appellant in this rent authority case?"
    print(f"[*] Querying RAG engine with question: '{query}' scoped to IDs: {doc_ids}")
    
    chat_payload = {
        "query": query,
        "document_ids": doc_ids
    }
    
    chat_res = requests.post(f"{API_URL}/api/chat", headers=headers, json=chat_payload)
    print(f"[*] Response status code: {chat_res.status_code}")
    if chat_res.status_code == 200:
        result = chat_res.json()
        print("\n=== ANSWER ===")
        print(result.get("answer"))
        print("\n=== CITATIONS ===")
        print(json.dumps(result.get("citations"), indent=2))
    else:
        print(f"[!] RAG query failed: {chat_res.text}")

if __name__ == "__main__":
    test_rag()
