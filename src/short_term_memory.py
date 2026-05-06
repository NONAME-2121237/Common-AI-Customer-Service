import re
import time
from typing import Any, Dict, List, Optional
from config_manager import ConfigManager
from redis_client import RedisClient

class ShortTermMemory:
    def __init__(self, config: ConfigManager, redis_client: RedisClient):
        self.config = config
        self.redis_client = redis_client
        self.storage_limit = config.get("memory.short_term.storage_limit", 30)
        self.recall_limit = config.get("memory.short_term.recall_limit", 6)
        self.max_age_seconds = config.get("memory.short_term.max_age_seconds", 1800)
        self.importance_weights = config.get("memory.short_term.scoring.importance_weights", {})

    async def write(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        memory = await self.redis_client.get_short_term_memory(session_id)
        
        importance_score = self._calculate_importance(content, metadata)
        
        new_message = {
            "role": role,
            "content": content,
            "timestamp": int(time.time()),
            "importance_score": importance_score,
            "metadata": metadata or {}
        }
        
        memory.append(new_message)
        memory = self._prune_memory(memory)
        
        await self.redis_client.set_short_term_memory(session_id, memory)

    def _calculate_importance(self, content: str, metadata: Optional[Dict[str, Any]]) -> int:
        score = 0
        
        if self.importance_weights.get("has_order_number") and re.search(r"订单号[：:]?\s*[\d]{6,}", content):
            score += self.importance_weights["has_order_number"]
        
        if self.importance_weights.get("requested_remember") and "请记住" in content:
            score += self.importance_weights["requested_remember"]
        
        if metadata and isinstance(metadata, dict):
            if metadata.get("important", False):
                score += 5
        
        return min(score, 10)

    def _prune_memory(self, memory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = int(time.time())
        
        valid_messages = [
            msg for msg in memory 
            if now - msg["timestamp"] <= self.max_age_seconds
        ]
        
        if len(valid_messages) <= self.storage_limit:
            return valid_messages
        
        scored_messages = []
        for msg in valid_messages:
            age = now - msg["timestamp"]
            time_factor = max(0, 1 - age / self.max_age_seconds)
            
            importance_normalized = msg["importance_score"] / 10
            
            retention_score = (time_factor * 0.4) + (importance_normalized * 0.6)
            scored_messages.append((retention_score, msg))
        
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        return [msg for _, msg in scored_messages[:self.storage_limit]]

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        memory = await self.redis_client.get_short_term_memory(session_id)
        return memory[-self.recall_limit:]

    async def clear(self, session_id: str):
        await self.redis_client.delete_short_term_memory(session_id)

    async def get_all(self, session_id: str) -> List[Dict[str, Any]]:
        return await self.redis_client.get_short_term_memory(session_id)

    async def update_config(self):
        self.storage_limit = self.config.get("memory.short_term.storage_limit", 30)
        self.recall_limit = self.config.get("memory.short_term.recall_limit", 6)
        self.max_age_seconds = self.config.get("memory.short_term.max_age_seconds", 1800)
        self.importance_weights = self.config.get("memory.short_term.scoring.importance_weights", {})
