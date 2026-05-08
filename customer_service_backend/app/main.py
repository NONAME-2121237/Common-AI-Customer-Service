import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_config_manager
from app.config.hot_reloader import ConfigHotReloader
from app.memory import RedisShortTermMemory, RedisConversationHistory, SessionManager
from app.tasks import TaskExecutor
from app.agents import CustomerServiceAgent
from app.routing import MessageForwarder
from app.auth import user_store
from app.auth.routes import router as auth_router, get_current_user
from app.auth.user_routes import router as user_router
from app.admin import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

memory: RedisShortTermMemory = None
conversation_history: RedisConversationHistory = None
session_manager: SessionManager = None
task_executor: TaskExecutor = None
agent: CustomerServiceAgent = None
forwarder: MessageForwarder = None
config_manager = None
hot_reloader = None

class ChatRequest(BaseModel):
    user_id: str
    user_input: str

class ChatResponse(BaseModel):
    response: str
    session_id: str
    user_id: str
    should_escalate: bool = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory, conversation_history, session_manager, task_executor, agent, forwarder, config_manager, hot_reloader
    
    config_manager = get_config_manager()
    
    def on_config_reload():
        logger.info("Configuration reloaded")
    
    hot_reloader = ConfigHotReloader(
        config_path='config.yaml',
        callback=lambda: config_manager.reload()
    )
    hot_reloader.start()
    
    memory = RedisShortTermMemory()
    conversation_history = RedisConversationHistory()
    session_manager = SessionManager()
    task_executor = TaskExecutor()
    forwarder = MessageForwarder()
    
    agent = CustomerServiceAgent(memory, conversation_history, task_executor)
    
    logger.info("Application started")
    
    yield
    
    if memory:
        await memory.close()
    if conversation_history:
        await conversation_history.close()
    if session_manager:
        await session_manager.close()
    if hot_reloader:
        hot_reloader.stop()
    
    logger.info("Application shutdown")

app = FastAPI(title="Customer Service Backend", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)

@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = await session_manager.get_or_create_session(request.user_id)
        
        session_state = await session_manager.get_session_state(session_id)
        
        if session_state and session_state.get('status') == 'transferred':
            await forwarder.forward_message(
                session_id=session_id,
                user_id=request.user_id,
                message=request.user_input,
                conversation_history=await conversation_history.get_history(session_id)
            )
            
            return ChatResponse(
                response="您当前在人工客服，请稍候...",
                session_id=session_id,
                user_id=request.user_id,
                should_escalate=True
            )
        
        result = await agent.process(
            session_id=session_id,
            user_id=request.user_id,
            user_input=request.user_input
        )
        
        return ChatResponse(
            response=result['response'],
            session_id=session_id,
            user_id=request.user_id,
            should_escalate=result.get('should_escalate', False)
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
