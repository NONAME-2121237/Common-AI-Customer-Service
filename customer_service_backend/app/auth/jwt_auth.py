import jwt
import time
from typing import Optional, Dict, Any

SECRET_KEY = "customer-service-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 86400

def create_token(user_id: str, username: str, role: str, permissions: list) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "permissions": permissions,
        "exp": time.time() + TOKEN_EXPIRE_SECONDS,
        "iat": time.time()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    payload = verify_token(token)
    if not payload:
        return None
    
    return {
        "id": payload.get("user_id"),
        "username": payload.get("username"),
        "role": payload.get("role"),
        "permissions": payload.get("permissions", [])
    }
