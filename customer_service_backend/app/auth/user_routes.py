from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import hashlib

from .user_store import user_store
from .routes import get_current_user
from .jwt_auth import create_token

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    permissions: Optional[List[str]] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    status: Optional[str] = None

class UserRoleUpdate(BaseModel):
    role: str
    permissions: List[str]

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@router.get("", response_model=List[dict])
async def list_users(current_user: dict = Depends(get_current_user)):
    if 'manage_users' not in current_user.get('permissions', []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    users = user_store.list_users()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "permissions": u.permissions,
            "status": u.status,
            "createdAt": u.created_at,
            "lastLogin": u.last_login
        }
        for u in users
    ]

@router.get("/{user_id}", response_model=dict)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if 'manage_users' not in current_user.get('permissions', []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    user = user_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "permissions": user.permissions,
        "status": user.status,
        "createdAt": user.created_at,
        "lastLogin": user.last_login
    }

@router.post("", response_model=dict)
async def create_user(user_data: UserCreate, current_user: dict = Depends(get_current_user)):
    if 'manage_users' not in current_user.get('permissions', []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if user_data.role == 'super_admin' and current_user.get('role') != 'super_admin':
        raise HTTPException(status_code=403, detail="Cannot create super_admin")
    
    if user_data.role == 'super_admin' and current_user.get('role') != 'super_admin':
        raise HTTPException(status_code=403, detail="Only super_admin can create super_admin")
    
    from .user_store import User
    import uuid
    
    if user_data.username in [u.username for u in user_store.list_users()]:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    user = user_store.create_user(
        username=user_data.username,
        password=user_data.password,
        role=user_data.role,
        permissions=user_data.permissions or []
    )
    
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create user")
    
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "permissions": user.permissions,
        "status": user.status,
        "createdAt": user.created_at
    }

@router.put("/{user_id}", response_model=dict)
async def update_user(user_id: str, user_data: UserUpdate, current_user: dict = Depends(get_current_user)):
    if 'manage_users' not in current_user.get('permissions', []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    user = user_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role == 'super_admin' and current_user.get('role') != 'super_admin':
        raise HTTPException(status_code=403, detail="Cannot modify super_admin")
    
    updates = {}
    if user_data.username:
        updates['username'] = user_data.username
    if user_data.password:
        updates['password'] = user_data.password
    if user_data.role:
        if user.role == 'super_admin' and current_user.get('role') != 'super_admin':
            raise HTTPException(status_code=403, detail="Cannot change super_admin role")
        updates['role'] = user_data.role
    if user_data.permissions:
        updates['permissions'] = user_data.permissions
    if user_data.status:
        updates['status'] = user_data.status
    
    user_store.update_user(user.username, updates)
    
    updated_user = user_store.get_user_by_id(user_id)
    return {
        "id": updated_user.id,
        "username": updated_user.username,
        "role": updated_user.role,
        "permissions": updated_user.permissions,
        "status": updated_user.status
    }

@router.put("/{user_id}/role")
async def update_user_role(user_id: str, role_data: UserRoleUpdate, current_user: dict = Depends(get_current_user)):
    if current_user.get('role') != 'super_admin' and 'assign_roles' not in current_user.get('permissions', []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    user = user_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role == 'super_admin':
        raise HTTPException(status_code=403, detail="Cannot modify super_admin")
    
    if role_data.role == 'super_admin' and current_user.get('role') != 'super_admin':
        raise HTTPException(status_code=403, detail="Only super_admin can assign super_admin role")
    
    user_store.update_user(user.username, {
        'role': role_data.role,
        'permissions': role_data.permissions
    })
    
    return {"status": "success"}

@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if 'manage_users' not in current_user.get('permissions', []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    user = user_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role == 'super_admin':
        raise HTTPException(status_code=403, detail="Cannot delete super_admin")
    
    if user.username == current_user.get('username'):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    success = user_store.delete_user(user.username)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete user")
    
    return {"status": "success"}
