import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_config_manager
from app.admin import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Admin API starting...")
    yield
    logger.info("Admin API shutting down...")

app = FastAPI(
    title="Customer Service Admin API",
    lifespan=lifespan
)

app.include_router(admin_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "admin"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
