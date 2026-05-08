from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.providers import get_provider_manager
from app.tasks import get_task_executor

router = APIRouter(prefix="/providers", tags=["providers"])

@router.get("")
async def list_providers():
    try:
        provider_manager = get_provider_manager()
        providers = provider_manager.list_providers()
        return {"providers": providers, "count": len(providers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_models():
    try:
        provider_manager = get_provider_manager()
        models = provider_manager.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    try:
        provider_manager = get_provider_manager()
        health = await provider_manager.health_check_all()
        return {"health": health}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

router_tasks = APIRouter(prefix="/tasks", tags=["tasks"])

@router_tasks.get("")
async def list_tasks():
    try:
        task_executor = get_task_executor()
        tasks = task_executor.list_tasks()
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router_tasks.post("/{task}/model")
async def update_task_model(task: str, model_id: str):
    try:
        task_executor = get_task_executor()
        success = await task_executor.update_task_model(task, model_id)
        if success:
            return {"status": "success", "task": task, "model": model_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to update task model")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/components/status")
async def component_status():
    try:
        provider_manager = get_provider_manager()
        providers = await provider_manager.health_check_all()
        
        return {
            "providers": providers,
            "status": "healthy" if all(providers.values()) else "degraded"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
