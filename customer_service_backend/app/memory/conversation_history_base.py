from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ConversationHistory(ABC):
    @abstractmethod
    async def add_messages(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        pass
    
    @abstractmethod
    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def reset(self, session_id: str) -> None:
        pass
