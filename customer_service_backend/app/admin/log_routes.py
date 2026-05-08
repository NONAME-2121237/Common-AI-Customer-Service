from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.auth.routes import get_current_user

router = APIRouter(prefix="/logs", tags=["logs"])

class LogLevelUpdate(BaseModel):
    level: str

@router.get("")
async def get_logs(lines: Optional[int] = 100, current_user: dict = Depends(get_current_user)):
    try:
        log_file = "logs/app.log"
        
        if not os.path.exists(log_file):
            return {"logs": [], "message": "Log file not found"}
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {"logs": recent_lines, "count": len(recent_lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/level")
async def update_log_level(update: LogLevelUpdate, current_user: dict = Depends(get_current_user)):
    try:
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        level = update.level.upper()
        
        if level not in valid_levels:
            raise HTTPException(status_code=400, detail=f"Invalid level. Must be one of: {valid_levels}")
        
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, level))
        
        for handler in logger.handlers:
            handler.setLevel(getattr(logging, level))
        
        return {"status": "success", "level": level}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
