import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from config_manager import ConfigManager
from redis_client import RedisClient
from provider_manager import ProviderManager
from task_executor import TaskExecutor
from agent_orchestrator import AgentOrchestrator
from short_term_memory import ShortTermMemory
from chat_log import ChatLog
from forward_service import ForwardService, PushService
from session_router import SessionRouter

from api.main_api import app as main_app, init_dependencies as init_main_deps
from api.admin_api import app as admin_app, init_dependencies as init_admin_deps

structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

async def init_all_components():
    logger.info("Initializing components...")
    
    config = ConfigManager("config/config.yaml")
    logger.info("Config manager initialized")
    
    redis_client = RedisClient(config)
    await redis_client.connect()
    logger.info("Redis client connected")
    
    provider_manager = ProviderManager(config)
    await provider_manager.init_providers()
    logger.info("Provider manager initialized")
    
    task_executor = TaskExecutor(config, provider_manager)
    logger.info("Task executor initialized")
    
    agent_orchestrator = AgentOrchestrator(config, task_executor)
    logger.info("Agent orchestrator initialized")
    
    forward_service = ForwardService(config)
    push_service = PushService(config)
    logger.info("Forward and push services initialized")
    
    short_term_memory = ShortTermMemory(config, redis_client)
    chat_log = ChatLog(redis_client)
    logger.info("Memory and chat log initialized")
    
    session_router = SessionRouter(config, redis_client, short_term_memory, chat_log, forward_service)
    logger.info("Session router initialized")
    
    init_main_deps(
        config=config,
        redis_client=redis_client,
        provider_manager=provider_manager,
        task_executor=task_executor,
        agent_orchestrator=agent_orchestrator,
        session_router=session_router,
        short_term_memory=short_term_memory,
        chat_log=chat_log,
        forward_service=forward_service,
        push_service=push_service
    )
    
    init_admin_deps(
        config=config,
        redis_client=redis_client,
        session_router=session_router,
        short_term_memory=short_term_memory,
        chat_log=chat_log,
        provider_manager=provider_manager,
        task_executor=task_executor
    )
    
    logger.info("All components initialized successfully")
    
    return {
        "config": config,
        "redis_client": redis_client,
        "provider_manager": provider_manager,
        "task_executor": task_executor,
        "agent_orchestrator": agent_orchestrator,
        "session_router": session_router,
        "short_term_memory": short_term_memory,
        "chat_log": chat_log,
        "forward_service": forward_service,
        "push_service": push_service
    }

async def start_services():
    components = await init_all_components()
    
    main_config = uvicorn.Config(main_app, host="0.0.0.0", port=8000, loop="asyncio")
    admin_config = uvicorn.Config(admin_app, host="127.0.0.1", port=8001, loop="asyncio")
    
    main_server = uvicorn.Server(main_config)
    admin_server = uvicorn.Server(admin_config)
    
    logger.info("Starting main API server on port 8000")
    logger.info("Starting admin API server on port 8001 (localhost only)")
    
    await asyncio.gather(
        main_server.serve(),
        admin_server.serve()
    )

if __name__ == "__main__":
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
