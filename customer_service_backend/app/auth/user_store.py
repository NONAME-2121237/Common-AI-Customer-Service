import hashlib
import secrets
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
import os

@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: str
    permissions: List[str]
    status: str
    created_at: float
    last_login: Optional[float] = None

class UserStore:
    def __init__(self, storage_path: str = "data/users.json"):
        self.storage_path = storage_path
        self._users: Dict[str, User] = {}
        self._load()
    
    def _load(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for user_data in data.get('users', []):
                        user = User(
                            id=user_data['id'],
                            username=user_data['username'],
                            password_hash=user_data['password_hash'],
                            role=user_data['role'],
                            permissions=user_data.get('permissions', []),
                            status=user_data.get('status', 'active'),
                            created_at=user_data.get('created_at', time.time()),
                            last_login=user_data.get('last_login')
                        )
                        self._users[user.username] = user
            except Exception as e:
                print(f"Failed to load users: {e}")
        
        if not self._users:
            self._create_default_admin()
    
    def _save(self):
        data = {
            'users': [
                {
                    'id': u.id,
                    'username': u.username,
                    'password_hash': u.password_hash,
                    'role': u.role,
                    'permissions': u.permissions,
                    'status': u.status,
                    'created_at': u.created_at,
                    'last_login': u.last_login
                }
                for u in self._users.values()
            ]
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _create_default_admin(self):
        admin = User(
            id='1',
            username='admin',
            password_hash=self._hash_password('admin123'),
            role='super_admin',
            permissions=['view_sessions', 'chat_sessions', 'reply_sessions', 'manage_users', 'manage_config', 'assign_roles', 'manage_admins'],
            status='active',
            created_at=time.time()
        )
        self._users['admin'] = admin
        self._save()
    
    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        return self._hash_password(password) == password_hash
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self._users.get(username)
        if not user:
            return None
        
        if user.status != 'active':
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
        
        user.last_login = time.time()
        self._save()
        
        return user
    
    def get_user(self, username: str) -> Optional[User]:
        return self._users.get(username)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        for user in self._users.values():
            if user.id == user_id:
                return user
        return None
    
    def create_user(self, username: str, password: str, role: str, permissions: List[str]) -> Optional[User]:
        if username in self._users:
            return None
        
        import uuid
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=self._hash_password(password),
            role=role,
            permissions=permissions,
            status='active',
            created_at=time.time()
        )
        self._users[username] = user
        self._save()
        
        return user
    
    def update_user(self, username: str, updates: Dict[str, Any]) -> bool:
        user = self._users.get(username)
        if not user:
            return False
        
        if 'password' in updates:
            updates['password_hash'] = self._hash_password(updates.pop('password'))
        
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        self._save()
        return True
    
    def delete_user(self, username: str) -> bool:
        if username not in self._users:
            return False
        
        user = self._users[username]
        if user.role == 'super_admin':
            return False
        
        del self._users[username]
        self._save()
        return True
    
    def list_users(self) -> List[User]:
        return list(self._users.values())

user_store = UserStore()
