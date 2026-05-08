from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.auth.routes import get_current_user
import os

if os.environ.get("USE_SIMPLE_MEMORY", "true").lower() == "true":
    from app.memory.simple import SimpleSessionManager, SimpleMemory, SimpleConversationHistory
    SessionMgrClass = SimpleSessionManager
    MemoryClass = SimpleMemory
    HistoryClass = SimpleConversationHistory
else:
    from app.memory.redis_score import RedisShortTermMemory
    from app.memory.conversation_history import RedisConversationHistory
    from app.memory.session_manager import SessionManager
    SessionMgrClass = SessionManager
    MemoryClass = RedisShortTermMemory
    HistoryClass = RedisConversationHistory

router = APIRouter(prefix="/session", tags=["session"])

class TransferRequest(BaseModel):
    user_id: str

class ReleaseRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    clear_memory: bool = False

class ClearRequest(BaseModel):
    session_id: str

class PruneRequest(BaseModel):
    session_id: str

async def get_session_manager():
    return SessionMgrClass()

async def get_memory():
    return MemoryClass()

async def get_conversation_history():
    return HistoryClass()

@router.get("/transferred")
async def list_transferred_sessions(
    current_user: dict = Depends(get_current_user),
    session_mgr = Depends(get_session_manager)
):
    try:
        sessions = await session_mgr.list_transferred_sessions()
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/release")
async def release_session(
    request: ReleaseRequest,
    current_user: dict = Depends(get_current_user),
    session_mgr = Depends(get_session_manager)
):
    try:
        session_id = request.session_id
        if not session_id and request.user_id:
            user_session = await session_mgr.get_user_session(request.user_id)
            if user_session:
                session_id = user_session.get('session_id')

        if not session_id:
            raise HTTPException(status_code=400, detail="session_id or user_id required")

        await session_mgr.release_session(session_id)

        if request.clear_memory:
            await session_mgr.clear_session(session_id)

        return {"status": "success", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transfer")
async def transfer_session(
    request: TransferRequest,
    current_user: dict = Depends(get_current_user),
    session_mgr = Depends(get_session_manager),
    memory = Depends(get_memory)
):
    try:
        session_id = await session_mgr.get_or_create_session(request.user_id)

        await memory.reset(session_id)
        await session_mgr.set_session_transferred(session_id)

        return {"status": "success", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear")
async def clear_session(
    request: ClearRequest,
    current_user: dict = Depends(get_current_user),
    session_mgr = Depends(get_session_manager)
):
    try:
        await session_mgr.clear_session(request.session_id)
        return {"status": "success", "session_id": request.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/prune")
async def prune_memory(
    request: PruneRequest,
    current_user: dict = Depends(get_current_user),
    memory = Depends(get_memory)
):
    try:
        await memory.clear(request.session_id)
        return {"status": "success", "session_id": request.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
