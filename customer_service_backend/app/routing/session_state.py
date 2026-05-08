from typing import Optional
from pydantic import BaseModel

class SessionState(BaseModel):
    status: str = "active"
    user_id: str = ""
    session_id: str = ""
    created_at: float = 0.0
    last_active: float = 0.0
    transferred_at: Optional[float] = None
    auto_release_at: Optional[float] = None
    reason: Optional[str] = None
    memory_frozen: bool = False
