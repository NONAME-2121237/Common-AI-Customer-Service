from typing import Dict, List, Any, Optional
import asyncio
import time

class SimpleMemory:
    def __init__(self):
        self._storage: Dict[str, List[Dict[str, Any]]] = {}
        self._timestamps: Dict[str, float] = {}

    async def add(self, session_id: str, content: str, role: str = "user", metadata: Optional[Dict] = None) -> None:
        if session_id not in self._storage:
            self._storage[session_id] = []
        self._storage[session_id].append({
            "content": content,
            "role": role,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })
        self._timestamps[session_id] = time.time()

    async def get(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self._storage.get(session_id, [])[-limit:]

    async def clear(self, session_id: str) -> None:
        if session_id in self._storage:
            self._storage[session_id] = []
        if session_id in self._timestamps:
            del self._timestamps[session_id]

    async def reset(self, session_id: str) -> None:
        await self.clear(session_id)

    async def close(self) -> None:
        pass


class SimpleConversationHistory:
    def __init__(self):
        self._storage: Dict[str, List[Dict[str, Any]]] = {}

    async def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        if session_id not in self._storage:
            self._storage[session_id] = []
        self._storage[session_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })

    async def get_history(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._storage.get(session_id, [])[-limit:]

    async def clear_history(self, session_id: str) -> None:
        if session_id in self._storage:
            self._storage[session_id] = []

    async def close(self) -> None:
        pass


class SimpleSessionManager:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._user_sessions: Dict[str, str] = {}

    async def get_or_create_session(self, user_id: str) -> str:
        if user_id in self._user_sessions:
            session_id = self._user_sessions[user_id]
            if session_id in self._sessions:
                return session_id

        import uuid
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "status": "active",
            "created_at": time.time(),
            "updated_at": time.time()
        }
        self._user_sessions[user_id] = session_id
        return session_id

    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        session_id = self._user_sessions.get(user_id)
        if session_id:
            return self._sessions.get(session_id)
        return None

    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    async def set_session_transferred(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["status"] = "transferred"
            self._sessions[session_id]["updated_at"] = time.time()

    async def release_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["status"] = "released"

    async def clear_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["status"] = "cleared"

    async def list_transferred_sessions(self) -> List[Dict[str, Any]]:
        return [s for s in self._sessions.values() if s.get("status") == "transferred"]

    async def close(self) -> None:
        pass
