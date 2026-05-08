from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional

class Provider(ABC):
    def __init__(self, provider_id: str, base_url: str, api_key: str, timeout: int = 30):
        self.provider_id = provider_id
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
    
    @abstractmethod
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **params
    ) -> str:
        pass
    
    @abstractmethod
    async def stream_chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **params
    ) -> AsyncIterator[str]:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass
    
    def get_model_config(self, model: str) -> Optional[Dict[str, Any]]:
        return None
