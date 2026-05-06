from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from config_manager import ConfigManager
from redis_client import RedisClient
from session_router import SessionRouter
from short_term_memory import ShortTermMemory
from chat_log import ChatLog
from provider_manager import ProviderManager
from task_executor import TaskExecutor
import os
import structlog

app = FastAPI(title="智能客服后端 - 管理 API")
security = HTTPBearer()

logger = structlog.get_logger()

class Dependencies:
    config: ConfigManager = None
    redis_client: RedisClient = None
    session_router: SessionRouter = None
    short_term_memory: ShortTermMemory = None
    chat_log: ChatLog = None
    provider_manager: ProviderManager = None
    task_executor: TaskExecutor = None

def init_dependencies(config: ConfigManager, redis_client: RedisClient,
                      session_router: SessionRouter, short_term_memory: ShortTermMemory,
                      chat_log: ChatLog, provider_manager: ProviderManager,
                      task_executor: TaskExecutor):
    Dependencies.config = config
    Dependencies.redis_client = redis_client
    Dependencies.session_router = session_router
    Dependencies.short_term_memory = short_term_memory
    Dependencies.chat_log = chat_log
    Dependencies.provider_manager = provider_manager
    Dependencies.task_executor = task_executor

async def verify_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = Dependencies.config.get("admin.api_key", "")
    if not api_key:
        return
    if credentials.credentials != api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

class ConfigUpdateRequest(BaseModel):
    path: str
    value: Any

class RawConfigRequest(BaseModel):
    raw_yaml: str

class ModelUpdateRequest(BaseModel):
    model_id: str

class SessionActionRequest(BaseModel):
    session_id: str
    reason: Optional[str] = None

class LogLevelRequest(BaseModel):
    level: str

@app.get("/admin/config")
async def get_config(credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    return Dependencies.config.get_desensitized_config()

@app.put("/admin/config")
async def update_config(request: ConfigUpdateRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    Dependencies.config.set(request.path, request.value)
    return {"success": True}

@app.get("/admin/config/raw")
async def get_raw_config(credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    return {"raw_yaml": Dependencies.config.get_raw_yaml()}

@app.put("/admin/config/raw")
async def set_raw_config(request: RawConfigRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    Dependencies.config.set_raw_yaml(request.raw_yaml)
    await Dependencies.provider_manager.reload()
    return {"success": True}

@app.get("/admin/providers")
async def get_providers(credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    providers = Dependencies.provider_manager.get_all_providers()
    for p in providers:
        if 'base_url' in p:
            p['base_url'] = '***'
    return providers

@app.get("/admin/models")
async def get_models(credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    return Dependencies.provider_manager.get_all_models()

@app.get("/admin/tasks")
async def get_tasks(credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    return Dependencies.task_executor.get_all_tasks()

@app.post("/admin/tasks/{task_name}/model")
async def update_task_model(task_name: str, request: ModelUpdateRequest, 
                            credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    Dependencies.config.set(f"tasks.{task_name}.model", request.model_id)
    return {"success": True}

@app.get("/admin/components/status")
async def get_component_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    try:
        await Dependencies.redis_client.client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"
    
    return {
        "redis": redis_status,
        "providers": len(Dependencies.provider_manager.get_all_providers()),
        "config": "loaded"
    }

@app.post("/admin/reboot/component")
async def reboot_component(request: Dict[str, str], credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    component = request.get("component", "")
    
    if component == "provider_manager":
        await Dependencies.provider_manager.reload()
        return {"success": True, "message": "Provider manager reloaded"}
    
    return {"success": False, "message": f"Unknown component: {component}"}

@app.get("/admin/sessions")
async def get_sessions(status: Optional[str] = None, user_id: Optional[str] = None,
                       limit: int = 20, offset: int = 0, 
                       credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    
    all_sessions = await Dependencies.redis_client.get_all_sessions()
    sessions_data = []
    
    for session_id in all_sessions:
        state = await Dependencies.redis_client.get_session_state(session_id)
        
        if status and state.get("status") != status:
            continue
        if user_id and state.get("user_id") != user_id:
            continue
        
        message_count = await Dependencies.chat_log.get_message_count(session_id)
        sessions_data.append({
            "session_id": session_id,
            "user_id": state.get("user_id", ""),
            "status": state.get("status", "active"),
            "created_at": state.get("created_at", 0),
            "last_active": state.get("last_active", 0),
            "memory_frozen": state.get("memory_frozen", False),
            "message_count": message_count
        })
    
    sessions_data.sort(key=lambda x: x["last_active"], reverse=True)
    
    total = len(sessions_data)
    sessions_data = sessions_data[offset:offset+limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "sessions": sessions_data
    }

@app.get("/admin/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 20, offset: int = 0,
                               credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    
    state = await Dependencies.redis_client.get_session_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = await Dependencies.chat_log.get_messages(session_id, limit, offset)
    total = await Dependencies.chat_log.get_message_count(session_id)
    
    return {
        "session_id": session_id,
        "user_id": state.get("user_id", ""),
        "total": total,
        "limit": limit,
        "offset": offset,
        "messages": messages
    }

@app.get("/admin/sessions/transferred")
async def get_transferred_sessions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    return await get_sessions(status="transferred", credentials=credentials)

@app.post("/admin/session/release")
async def release_transfer(request: SessionActionRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    await Dependencies.session_router.release_transfer(request.session_id)
    return {"success": True}

@app.post("/admin/session/transfer")
async def force_transfer(request: SessionActionRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    result = await Dependencies.session_router.transfer_to_human(request.session_id)
    return {"success": result.get("success", False)}

@app.post("/admin/session/clear")
async def clear_memory(request: SessionActionRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    await Dependencies.short_term_memory.clear(request.session_id)
    return {"success": True}

@app.post("/admin/session/delete")
async def delete_session(request: SessionActionRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    state = await Dependencies.redis_client.get_session_state(request.session_id)
    user_id = state.get("user_id", "")
    
    await Dependencies.short_term_memory.clear(request.session_id)
    await Dependencies.chat_log.delete(request.session_id)
    await Dependencies.redis_client.delete_session_state(request.session_id)
    await Dependencies.redis_client.delete_user_session(user_id)
    
    return {"success": True}

@app.get("/admin/logs")
async def get_logs(lines: int = 100, credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    log_file = Dependencies.config.get("admin.log_file", "logs/app.log")
    
    if not os.path.exists(log_file):
        return {"logs": [], "message": "Log file not found"}
    
    with open(log_file, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    
    return {"logs": all_lines[-lines:]}

@app.post("/admin/logs/level")
async def set_log_level(request: LogLevelRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_auth(credentials)
    Dependencies.config.set("logging.level", request.level)
    
    import logging
    level = getattr(logging, request.level.upper(), logging.INFO)
    structlog.configure(logger_factory=structlog.stdlib.LoggerFactory())
    logging.getLogger().setLevel(level)
    
    return {"success": True}
