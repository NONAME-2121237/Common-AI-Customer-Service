import json
import uuid
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

import redis.asyncio as redis

from ..config import get_config_manager

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._config = get_config_manager()
        self._redis_url = self._config.get('memory.short_term.config.url', redis_url)
        self._auto_release_seconds = self._config.get('routing.transfer.auto_release_seconds', 600)
        self._ttl = self._config.get('memory.short_term.config.ttl', 7200)
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis
    
    def _get_user_session_key(self, user_id: str) -> str:
        return f"chat:user_session:{user_id}"
    
    def _get_session_state_key(self, session_id: str) -> str:
        return f"chat:session:{session_id}:route_state"
    
    async def get_or_create_session(self, user_id: str) -> str:
        r = await self._get_redis()
        user_session_key = self._get_user_session_key(user_id)
        
        existing_session = await r.get(user_session_key)
        if existing_session:
            session_data = json.loads(existing_session)
            
            if session_data.get('status') == 'transferred':
                if time.time() - session_data.get('last_active', 0) > self._auto_release_seconds:
                    await self.release_session(session_data['session_id'])
                else:
                    return session_data['session_id']
            else:
                await self._update_session_activity(session_data['session_id'])
                return session_data['session_id']
        
        session_id = str(uuid.uuid4())
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'status': 'active',
            'created_at': time.time(),
            'last_active': time.time()
        }
        
        await r.setex(user_session_key, self._ttl, json.dumps(session_data, ensure_ascii=False))
        
        await self._init_session_state(session_id, user_id)
        
        logger.info(f"Created new session {session_id} for user {user_id}")
        return session_id
    
    async def _init_session_state(self, session_id: str, user_id: str) -> None:
        r = await self._get_redis()
        state_key = self._get_session_state_key(session_id)
        
        state = {
            'status': 'active',
            'user_id': user_id,
            'created_at': time.time(),
            'last_active': time.time(),
            'memory_frozen': False
        }
        
        await r.setex(state_key, self._ttl, json.dumps(state, ensure_ascii=False))
    
    async def _update_session_activity(self, session_id: str) -> None:
        r = await self._get_redis()
        user_session_key = f"chat:user_session:*"
        
        async for key in r.scan_iter(match=user_session_key):
            data = await r.get(key)
            if data:
                session_data = json.loads(data)
                if session_data.get('session_id') == session_id:
                    session_data['last_active'] = time.time()
                    await r.setex(key, self._ttl, json.dumps(session_data, ensure_ascii=False))
                    break
        
        state_key = self._get_session_state_key(session_id)
        state_data = await r.get(state_key)
        if state_data:
            state = json.loads(state_data)
            state['last_active'] = time.time()
            await r.setex(state_key, self._ttl, json.dumps(state, ensure_ascii=False))
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        r = await self._get_redis()
        state_key = self._get_session_state_key(session_id)
        
        state_data = await r.get(state_key)
        if not state_data:
            return None
        
        return json.loads(state_data)
    
    async def get_user_id_by_session(self, session_id: str) -> Optional[str]:
        state = await self.get_session_state(session_id)
        return state.get('user_id') if state else None
    
    async def set_session_transferred(self, session_id: str) -> None:
        r = await self._get_redis()
        state_key = self._get_session_state_key(session_id)
        
        state_data = await r.get(state_key)
        if not state_data:
            logger.warning(f"Session state not found for {session_id}")
            return
        
        state = json.loads(state_data)
        state['status'] = 'transferred'
        state['transferred_at'] = time.time()
        state['auto_release_at'] = time.time() + self._auto_release_seconds
        state['last_active'] = time.time()
        state['memory_frozen'] = True
        
        await r.setex(state_key, self._ttl, json.dumps(state, ensure_ascii=False))
        logger.info(f"Session {session_id} set to transferred")
    
    async def release_session(self, session_id: str) -> None:
        r = await self._get_redis()
        state_key = self._get_session_state_key(session_id)
        
        state_data = await r.get(state_key)
        if state_data:
            state = json.loads(state_data)
            user_id = state.get('user_id')
            
            state['status'] = 'active'
            state['released_at'] = time.time()
            state['last_active'] = time.time()
            state['memory_frozen'] = False
            
            await r.setex(state_key, self._ttl, json.dumps(state, ensure_ascii=False))
            
            if user_id:
                user_session_key = self._get_user_session_key(user_id)
                user_data = await r.get(user_session_key)
                if user_data:
                    session_data = json.loads(user_data)
                    session_data['status'] = 'active'
                    session_data['last_active'] = time.time()
                    await r.setex(user_session_key, self._ttl, json.dumps(session_data, ensure_ascii=False))
            
            logger.info(f"Session {session_id} released")
    
    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        r = await self._get_redis()
        user_session_key = self._get_user_session_key(user_id)
        
        data = await r.get(user_session_key)
        if not data:
            return None
        
        return json.loads(data)
    
    async def list_transferred_sessions(self) -> List[Dict[str, Any]]:
        r = await self._get_redis()
        transferred = []
        
        async for key in r.scan_iter(match="chat:session:*:route_state"):
            data = await r.get(key)
            if data:
                state = json.loads(data)
                if state.get('status') == 'transferred':
                    transferred.append(state)
        
        return transferred
    
    async def clear_session(self, session_id: str) -> None:
        r = await self._get_redis()
        
        memory_key = f"chat:memory:{session_id}"
        await r.delete(memory_key)
        
        logger.info(f"Cleared memory for session {session_id}")
    
    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
