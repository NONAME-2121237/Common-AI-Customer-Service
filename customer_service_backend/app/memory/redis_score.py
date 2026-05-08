import json
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

import redis.asyncio as redis

from .base import Memory
from ..config import get_config_manager

logger = logging.getLogger(__name__)

class RedisShortTermMemory(Memory):
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._config = get_config_manager()
        self._redis_url = self._config.get('memory.short_term.config.url', redis_url)
        self._storage_limit = self._config.get('memory.short_term.config.storage_limit', 30)
        self._recall_limit = self._config.get('memory.short_term.config.recall_limit', 6)
        self._max_age_seconds = self._config.get('memory.short_term.config.max_age_seconds', 1800)
        self._importance_weights = self._config.get('memory.short_term.config.scoring.importance_weights', {})
        self._ttl = self._config.get('memory.short_term.config.ttl', 7200)
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis
    
    def _get_key(self, session_id: str) -> str:
        return f"chat:memory:{session_id}"
    
    def _get_frozen_key(self, session_id: str) -> str:
        return f"chat:memory:frozen:{session_id}"
    
    async def add_messages(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        frozen = await self.is_frozen(session_id)
        if frozen:
            logger.debug(f"Memory is frozen for session {session_id}, skipping add")
            return
        
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
                'timestamp': time.time(),
                'importance_score': await self._calculate_importance(msg),
                'metadata': msg.get('metadata', {})
            }
            current_messages.append(msg_with_meta)
        
        await r.setex(key, self._ttl, json.dumps(current_messages, ensure_ascii=False))
        
        await self._prune_if_needed(session_id, current_messages)
    
    async def _calculate_importance(self, message: Dict[str, Any]) -> float:
        content = message.get('content', '').lower()
        score = 5.0
        
        if self._importance_weights.get('has_order_number'):
            import re
            if re.search(r'订单[号#]?\s*[:：]?\s*[A-Z0-9]{8,}', content):
                score += self._importance_weights['has_order_number']
        
        if self._importance_weights.get('requested_remember'):
            if '请记住' in content or '记住' in content:
                score += self._importance_weights['requested_remember']
        
        if self._importance_weights.get('is_resolved_marker'):
            if '已解决' in content or '问题解决' in content:
                score += self._importance_weights['is_resolved_marker']
        
        return max(0.0, min(10.0, score))
    
    async def _prune_if_needed(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        current_time = time.time()
        
        needs_prune = len(messages) > self._storage_limit
        
        if not needs_prune:
            for msg in messages:
                age = current_time - msg.get('timestamp', 0)
                if age > self._max_age_seconds:
                    needs_prune = True
                    break
        
        if needs_prune:
            await self.prune(session_id)
    
    async def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        frozen = await self.is_frozen(session_id)
        if frozen:
            return []
        
        r = await self._get_redis()
        key = self._get_key(session_id)
        
        existing = await r.get(key)
        if not existing:
            return []
        
        messages = json.loads(existing)
        
        effective_limit = limit if limit is not None else self._recall_limit
        return messages[-effective_limit:] if effective_limit else messages
    
    async def reset(self, session_id: str) -> None:
        r = await self._get_redis()
        key = self._get_key(session_id)
        await r.delete(key)
        logger.info(f"Memory reset for session {session_id}")
    
    async def set_frozen(self, session_id: str, frozen: bool) -> None:
        r = await self._get_redis()
        frozen_key = self._get_frozen_key(session_id)
        
        if frozen:
            await r.setex(frozen_key, self._ttl, "1")
        else:
            await r.delete(frozen_key)
        
        logger.info(f"Memory frozen={frozen} for session {session_id}")
    
    async def is_frozen(self, session_id: str) -> bool:
        r = await self._get_redis()
        frozen_key = self._get_frozen_key(session_id)
        return await r.exists(frozen_key) > 0
    
    async def prune(self, session_id: str) -> None:
        r = await self._get_redis()
        key = self._get_key(session_id)
        
        existing = await r.get(key)
        if not existing:
            return
        
        messages = json.loads(existing)
        
        if len(messages) <= self._storage_limit:
            return
        
        current_time = time.time()
        scored_messages = []
        
        for msg in messages:
            age = current_time - msg.get('timestamp', 0)
            
            if age < self._max_age_seconds:
                time_factor = 1.0 - (age / self._max_age_seconds) * 0.5
            else:
                excess_age = age - self._max_age_seconds
                time_factor = max(0.1, 0.5 - (excess_age / self._max_age_seconds) * 0.4)
            
            importance = msg.get('importance_score', 5.0) / 10.0
            
            score = time_factor * 0.4 + importance * 0.6
            scored_messages.append((score, msg))
        
        scored_messages.sort(key=lambda x: x[0])
        
        kept_messages = scored_messages[-self._storage_limit:]
        kept_messages.sort(key=lambda x: x[1].get('timestamp', 0))
        
        result = [msg for _, msg in kept_messages]
        
        await r.setex(key, self._ttl, json.dumps(result, ensure_ascii=False))
        logger.info(f"Pruned memory for session {session_id}: {len(messages)} -> {len(result)}")
    
    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
