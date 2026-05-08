import httpx
import json
import logging
from typing import List, Dict, Any, AsyncIterator, Optional

from .base import Provider

logger = logging.getLogger(__name__)

class AnthropicProvider(Provider):
    def __init__(
        self, 
        provider_id: str, 
        base_url: str = "https://api.anthropic.com/v1", 
        api_key: str = "", 
        timeout: int = 30
    ):
        super().__init__(provider_id, base_url, api_key, timeout)
        self._default_params = {
            "temperature": 0.7,
            "max_tokens": 1024
        }
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **params
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        merged_params = {**self._default_params, **params}
        
        system_message = ""
        filtered_messages = []
        for msg in messages:
            if msg.get('role') == 'system':
                system_message = msg.get('content', '')
            else:
                filtered_messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
        payload = {
            "model": model,
            "messages": filtered_messages,
            **merged_params
        }
        
        if system_message:
            payload["system"] = system_message
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result['content'][0]['text']
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
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true"
        }
        
        merged_params = {**self._default_params, "stream": True, **params}
        
        system_message = ""
        filtered_messages = []
        for msg in messages:
            if msg.get('role') == 'system':
                system_message = msg.get('content', '')
            else:
                filtered_messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
        payload = {
            "model": model,
            "messages": filtered_messages,
            **merged_params
        }
        
        if system_message:
            payload["system"] = system_message
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            try:
                                chunk = json.loads(data)
                                if chunk.get('type') == 'content_block_delta':
                                    if chunk.get('delta', {}).get('type') == 'text_delta':
                                        yield chunk['delta']['text']
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"Error in stream for {self.provider_id}/{model}: {e}")
                raise
    
    async def health_check(self) -> bool:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        async with httpx.AsyncClient(timeout=5) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "test"}]
                    }
                )
                return response.status_code == 200
            except Exception as e:
                logger.warning(f"Health check failed for {self.provider_id}: {e}")
                return False
