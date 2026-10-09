import base64
import binascii
import hashlib
import hmac
import secrets

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$" + base64.urlsafe_b64encode(salt).decode().rstrip("=") + "$" + base64.urlsafe_b64encode(digest).decode().rstrip("=")

def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, work, salt_part, digest_part = encoded.split("$", 3)
        if algorithm != "scrypt" or work != "16384": return False
        salt = base64.urlsafe_b64decode(salt_part + "=" * (-len(salt_part) % 4))
        expected = base64.urlsafe_b64decode(digest_part + "=" * (-len(digest_part) % 4))
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=len(expected))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, binascii.Error):
        return False
