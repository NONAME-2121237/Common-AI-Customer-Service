import json
import logging
import time
from typing import List, Dict, Any, Optional

import redis.asyncio as redis

from .conversation_history_base import ConversationHistory
from ..config import get_config_manager

logger = logging.getLogger(__name__)

class RedisConversationHistory(ConversationHistory):
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._config = get_config_manager()
        self._redis_url = self._config.get('memory.short_term.config.url', redis_url)
        self._ttl = self._config.get('memory.short_term.config.ttl', 7200)
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis
    
    def _get_key(self, session_id: str) -> str:
        return f"chat:history:{session_id}"
    
    async def add_messages(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        r = await self._get_redis()
        key = self._get_key(session_id)
        
        existing = await r.get(key)
        current_messages = []
        if existing:
            current_messages = json.loads(existing)
        
        for msg in messages:
            msg_with_meta = {
                'role': msg.get('role', 'user'),
                'content': msg.get('content', ''),
                'timestamp': time.time()
            }
            if 'metadata' in msg:
                msg_with_meta['metadata'] = msg['metadata']
            current_messages.append(msg_with_meta)
        
        await r.setex(key, self._ttl, json.dumps(current_messages, ensure_ascii=False))
        logger.debug(f"Added {len(messages)} messages to history for session {session_id}")
    
    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        r = await self._get_redis()
        key = self._get_key(session_id)
        
        existing = await r.get(key)
        if not existing:
            return []
        
        return json.loads(existing)
    
    async def reset(self, session_id: str) -> None:
        r = await self._get_redis()
        key = self._get_key(session_id)
        await r.delete(key)
        logger.info(f"Conversation history reset for session {session_id}")
    
    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
