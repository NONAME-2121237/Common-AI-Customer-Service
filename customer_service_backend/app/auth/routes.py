from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
from functools import wraps

from .user_store import user_store
from .jwt_auth import create_token, get_user_from_token, verify_token

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    permissions: List[str]
    status: str

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization[7:]
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return get_user_from_token(token)

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user') or await func(*args, **kwargs)
            if permission not in user.get('permissions', []):
                raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
            return user
        return wrapper
    return decorator

def require_role(role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if user.get('role') == 'super_admin':
                return await func(*args, **kwargs)
            if user.get('role') != role:
                raise HTTPException(status_code=403, detail=f"Role required: {role}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = user_store.authenticate(request.username, request.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_token(user.id, user.username, user.role, user.permissions)
    
    return LoginResponse(
        token=token,
        user={
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "permissions": user.permissions,
            "status": user.status
        }
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user['id'],
        username=current_user['username'],
        role=current_user['role'],
        permissions=current_user['permissions'],
        status='active'
    )

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    return {"status": "success", "message": "Logged out successfully"}
