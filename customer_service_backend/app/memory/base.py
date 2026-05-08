from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class Memory(ABC):
    @abstractmethod
    async def add_messages(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        pass
    
    @abstractmethod
    async def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def reset(self, session_id: str) -> None:
        pass
    
    @abstractmethod
    async def set_frozen(self, session_id: str, frozen: bool) -> None:
        pass
    
    @abstractmethod
    async def is_frozen(self, session_id: str) -> bool:
        pass
    
    @abstractmethod
    async def prune(self, session_id: str) -> None:
        pass
