from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer, BadSignature
from .config import SECRET_KEY

# Use PBKDF2-SHA256 for portability and zero native deps
pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_ctx.verify(password, password_hash)

def make_session_token(user_id: int) -> str:
    s = URLSafeSerializer(SECRET_KEY, salt="session")
    return s.dumps({"uid": user_id})

def read_session_token(token: str) -> int | None:
    s = URLSafeSerializer(SECRET_KEY, salt="session")
    try:
        data = s.loads(token)
        return int(data.get("uid"))
    except (BadSignature, ValueError, TypeError):
        return None
