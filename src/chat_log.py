import time
from typing import Any, Dict, List, Optional
from redis_client import RedisClient

class ChatLog:
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client

    async def append(self, session_id: str, user_id: str, sender: str, content: str):
        message = {
            "sender": sender,
            "content": content,
            "timestamp": int(time.time())
        }
        await self.redis_client.append_chat_log(session_id, message)

    async def get_messages(self, session_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return await self.redis_client.get_chat_log(session_id, limit, offset)

    async def get_all_messages(self, session_id: str) -> List[Dict[str, Any]]:
        count = await self.get_message_count(session_id)
        return await self.redis_client.get_chat_log(session_id, count, 0)

    async def get_message_count(self, session_id: str) -> int:
        return await self.redis_client.get_chat_log_count(session_id)

    async def delete(self, session_id: str):
        await self.redis_client.delete_chat_log(session_id)
