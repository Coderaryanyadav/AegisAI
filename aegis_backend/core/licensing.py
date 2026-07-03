import json
import base64
import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# Embedded Public Key generated for AegisAI
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAbocsE12+Nps2iPbi24Dsm6dEfOODk0MMAXT3MpF9NB8=
-----END PUBLIC KEY-----"""

class LicenseValidator:
    @staticmethod
    def _get_public_key():
        return serialization.load_pem_public_key(PUBLIC_KEY_PEM)

    @staticmethod
    def verify_license(license_key: str) -> dict:
        """
        Verifies an Ed25519 signed license key.
        License Key Format: base64(payload_json) + "." + base64(signature)
        Returns the parsed payload dict if valid, raises ValueError if invalid.
        """
        try:
            payload_b64, signature_b64 = license_key.strip().split('.')
            payload_bytes = base64.b64decode(payload_b64)
            signature_bytes = base64.urlsafe_b64decode(signature_b64)
            
            public_key = LicenseValidator._get_public_key()
            public_key.verify(signature_bytes, payload_bytes)
            
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            # Check expiration
            exp_date_str = payload.get("expires_at")
            if exp_date_str:
                exp_date = datetime.datetime.fromisoformat(exp_date_str)
                if datetime.datetime.now(datetime.timezone.utc) > exp_date:
                    raise ValueError("License has expired.")
                    
            return payload
            
        except ValueError as e:
            if "expired" in str(e):
                raise
            raise ValueError("Invalid license format.")
        except InvalidSignature:
            raise ValueError("Cryptographic signature verification failed. License is forged or corrupted.")
        except Exception as e:
            raise ValueError(f"Error validating license: {str(e)}")
