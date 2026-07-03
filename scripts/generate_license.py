import json
import base64
import datetime
import sys
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Keep this private key strictly secure and do not share it.
PRIVATE_KEY_PEM = b"""-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIGjJhTsBd06yCJPp9euUt0PlbvNivoKAiwjZ3Swye1X8
-----END PRIVATE KEY-----"""

def generate_license(tier: str, licensee_name: str, valid_days: int) -> str:
    private_key = serialization.load_pem_private_key(PRIVATE_KEY_PEM, password=None)
    
    expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=valid_days)).isoformat()
    
    payload = {
        "tier": tier,
        "licensee": licensee_name,
        "issued_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "expires_at": expires_at,
        "version": "1.0"
    }
    
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    
    signature_bytes = private_key.sign(payload_bytes)
    
    payload_b64 = base64.b64encode(payload_bytes).decode('utf-8')
    signature_b64 = base64.urlsafe_b64encode(signature_bytes).decode('utf-8')
    
    return f"{payload_b64}.{signature_b64}"

if __name__ == "__main__":
    print("AegisAI Offline License Generator")
    print("=================================")
    licensee = input("Enter Licensee Name (e.g. Acme Law Firm): ").strip()
    tier = input("Enter Tier (e.g. Pro, Enterprise): ").strip() or "Enterprise"
    days_str = input("Enter Validity in Days (default 365): ").strip()
    days = int(days_str) if days_str.isdigit() else 365
    
    license_key = generate_license(tier, licensee, days)
    print("\n--- GENERATED LICENSE KEY ---")
    print(license_key)
    print("-----------------------------\n")
    print(f"This license is valid for {days} days.")
