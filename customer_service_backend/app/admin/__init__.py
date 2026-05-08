from fastapi import APIRouter

from .config_routes import router as config_router
from .session_routes import router as session_router
from .provider_routes import router as provider_router
from .log_routes import router as log_router

router = APIRouter(prefix="/admin", tags=["admin"])

router.include_router(config_router)
router.include_router(session_router)
router.include_router(provider_router)
router.include_router(log_router)
