import httpx
import json
import logging
from typing import List, Dict, Any, AsyncIterator, Optional

from .base import Provider

logger = logging.getLogger(__name__)

class OpenAICompatibleProvider(Provider):
    def __init__(
        self, 
        provider_id: str, 
        base_url: str, 
        api_key: str, 
        timeout: int = 30,
        models: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(provider_id, base_url, api_key, timeout)
        self._models_config: Dict[str, Dict[str, Any]] = {}
        if models:
            for model in models:
                self._models_config[model['name']] = model.get('default_params', {})
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **params
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        model_config = self.get_model_config(model)
        if model_config:
            params = {**model_config, **params}
        
        payload = {
            "model": model,
            "messages": messages,
            **params
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling {self.provider_id}/{model}: {e.response.status_code}")
                raise
            except Exception as e:
                logger.error(f"Error calling {self.provider_id}/{model}: {e}")
                raise
    
    async def stream_chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **params
    ) -> AsyncIterator[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        model_config = self.get_model_config(model)
        if model_config:
            params = {**model_config, **params}
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            **params
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield delta['content']
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"Error in stream for {self.provider_id}/{model}: {e}")
                raise
    
    async def health_check(self) -> bool:
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with httpx.AsyncClient(timeout=5) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                return response.status_code == 200
            except Exception as e:
                logger.warning(f"Health check failed for {self.provider_id}: {e}")
                return False
    
    def get_model_config(self, model: str) -> Optional[Dict[str, Any]]:
        return self._models_config.get(model)
    
    def add_model_config(self, model: str, config: Dict[str, Any]) -> None:
        self._models_config[model] = config
