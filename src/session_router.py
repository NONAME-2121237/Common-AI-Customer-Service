import time
import uuid
from typing import Any, Dict, Optional, Tuple
from config_manager import ConfigManager
from redis_client import RedisClient
from short_term_memory import ShortTermMemory
from chat_log import ChatLog
from forward_service import ForwardService

class SessionRouter:
    def __init__(self, config: ConfigManager, redis_client: RedisClient, 
                 short_term_memory: ShortTermMemory, chat_log: ChatLog,
                 forward_service: ForwardService):
        self.config = config
        self.redis_client = redis_client
        self.short_term_memory = short_term_memory
        self.chat_log = chat_log
        self.forward_service = forward_service
        self.max_idle_seconds = config.get("session.max_idle_seconds", 1800)
        self.auto_release_seconds = config.get("routing.transfer.auto_release_seconds", 600)
        self.clear_memory_on_transfer = config.get("routing.transfer.clear_memory_on_transfer", True)
        self.freeze_memory_during_transfer = config.get("routing.transfer.freeze_memory_during_transfer", True)

    async def get_or_create_session(self, user_id: str) -> Tuple[str, Dict[str, Any], bool]:
        session_id = await self.redis_client.get_user_session(user_id)
        is_new = False
        
        if session_id:
            session_state = await self.redis_client.get_session_state(session_id)
            
            if session_state:
                last_active = session_state.get("last_active", 0)
                if time.time() - last_active > self.max_idle_seconds:
                    await self._close_session(session_id, user_id)
                    session_id = None
        
        if not session_id:
            session_id = await self._create_session(user_id)
            is_new = True
        
        session_state = await self.redis_client.get_session_state(session_id)
        return session_id, session_state, is_new

    async def _create_session(self, user_id: str) -> str:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = int(time.time())
        
        await self.redis_client.set_user_session(user_id, session_id)
        await self.redis_client.set_session_state(session_id, {
            "status": "active",
            "user_id": user_id,
            "created_at": now,
            "last_active": now,
            "memory_frozen": False
        })
        
        return session_id

    async def _close_session(self, session_id: str, user_id: str):
        await self.short_term_memory.clear(session_id)
        await self.chat_log.delete(session_id)
        await self.redis_client.delete_session_state(session_id)
        await self.redis_client.delete_user_session(user_id)

    async def update_last_active(self, session_id: str):
        await self.redis_client.set_session_state(session_id, {"last_active": int(time.time())})

    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        return await self.redis_client.get_session_state(session_id)

    async def transfer_to_human(self, session_id: str) -> Dict[str, Any]:
        session_state = await self.redis_client.get_session_state(session_id)
        user_id = session_state.get("user_id", "")
        
        if self.clear_memory_on_transfer:
            await self.short_term_memory.clear(session_id)
        
        if self.freeze_memory_during_transfer:
            await self.redis_client.set_session_state(session_id, {"memory_frozen": True})
        
        messages = await self.chat_log.get_all_messages(session_id)
        for msg in messages:
            await self.forward_service.send_message(
                session_id=session_id,
                user_id=user_id,
                sender=msg["sender"],
                content=msg["content"],
                timestamp=msg["timestamp"]
            )
        
        now = int(time.time())
        await self.redis_client.set_session_state(session_id, {
            "status": "transferred",
            "transferred_at": now,
            "auto_release_at": now + self.auto_release_seconds,
            "last_active": now
        })
        
        return {
            "success": True,
            "message": "您的问题已转接人工客服，请稍候。"
        }

    async def release_transfer(self, session_id: str):
        await self.redis_client.set_session_state(session_id, {
            "status": "active",
            "memory_frozen": False,
            "transferred_at": 0,
            "auto_release_at": 0
        })

    async def check_auto_release(self, session_id: str) -> bool:
        session_state = await self.redis_client.get_session_state(session_id)
        
        if session_state.get("status") != "transferred":
            return False
        
        auto_release_at = session_state.get("auto_release_at", 0)
        if time.time() > auto_release_at:
            await self.release_transfer(session_id)
            return True
        
        return False

    async def check_idle_timeout(self, session_id: str, user_id: str) -> bool:
        session_state = await self.redis_client.get_session_state(session_id)
        last_active = session_state.get("last_active", 0)
        
        if time.time() - last_active > self.max_idle_seconds:
            await self._close_session(session_id, user_id)
            return True
        
        return False

    async def is_memory_frozen(self, session_id: str) -> bool:
        session_state = await self.redis_client.get_session_state(session_id)
        return session_state.get("memory_frozen", False)

    async def update_config(self):
        self.max_idle_seconds = self.config.get("session.max_idle_seconds", 1800)
        self.auto_release_seconds = self.config.get("routing.transfer.auto_release_seconds", 600)
        self.clear_memory_on_transfer = self.config.get("routing.transfer.clear_memory_on_transfer", True)
        self.freeze_memory_during_transfer = self.config.get("routing.transfer.freeze_memory_during_transfer", True)
