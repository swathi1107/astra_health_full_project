import hashlib, hmac, os, secrets
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
SECRET = os.getenv("SECRET_KEY", "development-only-change-me")
serializer = URLSafeTimedSerializer(SECRET, salt="astra-session")

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
    return f"pbkdf2_sha256${salt}${digest}"

def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$", 2)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
        return hmac.compare_digest(check, digest)
    except Exception:
        return False

def make_session(user_id: int) -> str:
    return serializer.dumps({"uid": user_id})

def read_session(token: str):
    try:
        return serializer.loads(token, max_age=60*60*12).get("uid")
    except (BadSignature, SignatureExpired, AttributeError):
        return None
