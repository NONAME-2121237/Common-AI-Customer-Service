import json
import redis
from typing import Any, Dict, List, Optional
from redis import asyncio as aioredis
from config_manager import ConfigManager

class RedisClient:
    def __init__(self, config: ConfigManager):
        self.config = config
        self._client: Optional[aioredis.Redis] = None
        self._sync_client: Optional[redis.Redis] = None

    async def connect(self):
        redis_config = self.config.get("redis", {})
        host = redis_config.get("host", "localhost")
        port = redis_config.get("port", 6379)
        db = redis_config.get("db", 0)
        
        self._client = await aioredis.from_url(f"redis://{host}:{port}/{db}")
        self._sync_client = redis.Redis(host=host, port=port, db=db)

    async def disconnect(self):
        if self._client:
            await self._client.close()
        if self._sync_client:
            self._sync_client.close()

    async def get_user_session(self, user_id: str) -> Optional[str]:
        key = f"user:session:{user_id}"
        return await self._client.get(key)

    async def set_user_session(self, user_id: str, session_id: str):
        key = f"user:session:{user_id}"
        await self._client.set(key, session_id)

    async def delete_user_session(self, user_id: str):
        key = f"user:session:{user_id}"
        await self._client.delete(key)

    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        key = f"session:{session_id}:state"
        data = await self._client.hgetall(key)
        if not data:
            return {}
        result = {}
        for k, v in data.items():
            k_str = k.decode('utf-8')
            v_str = v.decode('utf-8')
            if v_str.isdigit():
                result[k_str] = int(v_str)
            elif v_str == 'true':
                result[k_str] = True
            elif v_str == 'false':
                result[k_str] = False
            else:
                result[k_str] = v_str
        return result

    async def set_session_state(self, session_id: str, state: Dict[str, Any]):
        key = f"session:{session_id}:state"
        await self._client.hset(key, mapping=state)

    async def delete_session_state(self, session_id: str):
        key = f"session:{session_id}:state"
        await self._client.delete(key)

    async def get_short_term_memory(self, session_id: str) -> List[Dict[str, Any]]:
        key = f"memory:session:{session_id}"
        data = await self._client.get(key)
        if not data:
            return []
        return json.loads(data.decode('utf-8'))

    async def set_short_term_memory(self, session_id: str, memory: List[Dict[str, Any]]):
        key = f"memory:session:{session_id}"
        await self._client.set(key, json.dumps(memory))

    async def delete_short_term_memory(self, session_id: str):
        key = f"memory:session:{session_id}"
        await self._client.delete(key)

    async def append_chat_log(self, session_id: str, message: Dict[str, Any]):
        key = f"chatlog:session:{session_id}"
        await self._client.rpush(key, json.dumps(message))

    async def get_chat_log(self, session_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        key = f"chatlog:session:{session_id}"
        start = offset
        end = offset + limit - 1
        data = await self._client.lrange(key, start, end)
        return [json.loads(item.decode('utf-8')) for item in data]

    async def get_chat_log_count(self, session_id: str) -> int:
        key = f"chatlog:session:{session_id}"
        return await self._client.llen(key)

    async def delete_chat_log(self, session_id: str):
        key = f"chatlog:session:{session_id}"
        await self._client.delete(key)

    async def get_all_sessions(self) -> List[str]:
        pattern = "session:*:state"
        keys = await self._client.keys(pattern)
        return [key.decode('utf-8').replace('session:', '').replace(':state', '') for key in keys]

    async def flush_all(self):
        await self._client.flushdb()

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis client not connected")
        return self._client

    @property
    def sync_client(self) -> redis.Redis:
        if not self._sync_client:
            raise RuntimeError("Redis sync client not connected")
        return self._sync_client
