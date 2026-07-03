import os
import json
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def generate_root_keys():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    print("=== ED25519 ROOT KEY PAIR ===")
    print("PRIVATE KEY (KEEP THIS SECRET - DO NOT COMMIT TO GIT):")
    print(private_bytes.decode('utf-8'))
    print("\nPUBLIC KEY (EMBED THIS IN aegis_backend/core/licensing.py):")
    print(public_bytes.decode('utf-8'))
    
if __name__ == "__main__":
    generate_root_keys()
