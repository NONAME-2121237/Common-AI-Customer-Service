from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
from config_manager import ConfigManager
from redis_client import RedisClient
from session_router import SessionRouter
from short_term_memory import ShortTermMemory
from chat_log import ChatLog
from forward_service import ForwardService, PushService
from agent_orchestrator import AgentOrchestrator
from task_executor import TaskExecutor
from provider_manager import ProviderManager

app = FastAPI(title="智能客服后端 - 主 API")

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    user_id: str
    reply: str

class Dependencies:
    config: ConfigManager = None
    redis_client: RedisClient = None
    provider_manager: ProviderManager = None
    task_executor: TaskExecutor = None
    agent_orchestrator: AgentOrchestrator = None
    session_router: SessionRouter = None
    short_term_memory: ShortTermMemory = None
    chat_log: ChatLog = None
    forward_service: ForwardService = None
    push_service: PushService = None

def init_dependencies(config: ConfigManager, redis_client: RedisClient,
                      provider_manager: ProviderManager, task_executor: TaskExecutor,
                      agent_orchestrator: AgentOrchestrator, session_router: SessionRouter,
                      short_term_memory: ShortTermMemory, chat_log: ChatLog,
                      forward_service: ForwardService, push_service: PushService):
    Dependencies.config = config
    Dependencies.redis_client = redis_client
    Dependencies.provider_manager = provider_manager
    Dependencies.task_executor = task_executor
    Dependencies.agent_orchestrator = agent_orchestrator
    Dependencies.session_router = session_router
    Dependencies.short_term_memory = short_term_memory
    Dependencies.chat_log = chat_log
    Dependencies.forward_service = forward_service
    Dependencies.push_service = push_service

@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    deps = Dependencies
    
    session_id, session_state, is_new = await deps.session_router.get_or_create_session(request.user_id)
    
    await deps.session_router.update_last_active(session_id)
    
    if session_state.get("status") == "transferred":
        await deps.session_router.check_auto_release(session_id)
        
        session_state = await deps.session_router.get_session_state(session_id)
        if session_state.get("status") == "transferred":
            await deps.forward_service.send_message(
                session_id=session_id,
                user_id=request.user_id,
                sender="user",
                content=request.message
            )
            return ChatResponse(user_id=request.user_id, reply="")
    
    pre_guard_result = await deps.task_executor.execute(
        "pre_guard",
        message=request.message
    )
    
    if not pre_guard_result.get("safe", True):
        reply = "抱歉，您的请求不符合安全规范。"
        await deps.chat_log.append(session_id, request.user_id, "user", request.message)
        await deps.chat_log.append(session_id, request.user_id, "agent", reply)
        
        asyncio.create_task(deps.push_service.push_reply(session_id, request.user_id, reply))
        
        return ChatResponse(user_id=request.user_id, reply=reply)
    
    memory_frozen = await deps.session_router.is_memory_frozen(session_id)
    history = await deps.short_term_memory.get_history(session_id)
    
    agent_result = await deps.agent_orchestrator.run(
        user_id=request.user_id,
        session_id=session_id,
        message=request.message,
        history=history
    )
    
    reply = agent_result.get("response", "")
    should_transfer = agent_result.get("transfer", False)
    
    if should_transfer:
        transfer_result = await deps.session_router.transfer_to_human(session_id)
        reply = transfer_result.get("message", reply)
    
    await deps.chat_log.append(session_id, request.user_id, "user", request.message)
    await deps.chat_log.append(session_id, request.user_id, "agent", reply)
    
    if not memory_frozen:
        await deps.short_term_memory.write(session_id, "user", request.message)
        if reply:
            await deps.short_term_memory.write(session_id, "assistant", reply)
    
    asyncio.create_task(deps.push_service.push_reply(session_id, request.user_id, reply))
    
    return ChatResponse(user_id=request.user_id, reply=reply)
