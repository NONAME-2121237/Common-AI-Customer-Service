from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from ..config import get_config_manager

router = APIRouter(prefix="/config", tags=["config"])

class ConfigUpdate(BaseModel):
    path: str
    value: Any

class RawConfigUpdate(BaseModel):
    content: str

@router.get("")
async def get_config():
    config_manager = get_config_manager()
    config = config_manager.load()
    
    safe_config = {}
    if 'providers' in config:
        safe_config['providers'] = []
        for provider in config['providers']:
            safe_provider = provider.copy()
            if 'api_key' in safe_provider and safe_provider['api_key']:
                safe_provider['api_key'] = '***'
            safe_config['providers'].append(safe_provider)
    
    safe_config['models'] = config.get('models', {})
    safe_config['tasks'] = config.get('tasks', {})
    safe_config['memory'] = config.get('memory', {})
    safe_config['routing'] = config.get('routing', {})
    safe_config['security'] = config.get('security', {})
    safe_config['agent'] = config.get('agent', {})
    safe_config['admin'] = config.get('admin', {})
    
    return safe_config

@router.put("")
async def update_config(update: ConfigUpdate):
    config_manager = get_config_manager()
    try:
        config_manager.save_config({update.path: update.value})
        return {"status": "success", "updated": update.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/raw")
async def get_raw_config():
    config_manager = get_config_manager()
    return {"content": config_manager.get_raw()}

@router.put("/raw")
async def update_raw_config(update: RawConfigUpdate):
    config_manager = get_config_manager()
    try:
        with open('config.yaml', 'w', encoding='utf-8') as f:
            f.write(update.content)
        config_manager.reload()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
