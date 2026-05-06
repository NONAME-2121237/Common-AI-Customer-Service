import asyncio
import httpx
from typing import Any, Dict, Optional
from config_manager import ConfigManager

class ForwardService:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.forward_url = config.get("forward.url", "")
        self.forward_method = config.get("forward.method", "POST")
        self.forward_headers = config.get("forward.headers", {})
        self.forward_timeout = config.get("forward.timeout", 5)
        self.forward_retry = config.get("forward.retry", 2)

    async def send_message(self, session_id: str, user_id: str, sender: str, content: str, timestamp: Optional[int] = None):
        if not self.forward_url:
            return
        
        if timestamp is None:
            timestamp = int(asyncio.get_event_loop().time())
        
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "sender": sender,
            "content": content,
            "timestamp": timestamp
        }
        
        async with httpx.AsyncClient() as client:
            for attempt in range(self.forward_retry + 1):
                try:
                    response = await client.request(
                        method=self.forward_method,
                        url=self.forward_url,
                        json=payload,
                        headers=self.forward_headers,
                        timeout=self.forward_timeout
                    )
                    response.raise_for_status()
                    return response.json()
                except Exception as e:
                    if attempt < self.forward_retry:
                        await asyncio.sleep(1)
                        continue
                    raise e

    def update_config(self):
        self.forward_url = self.config.get("forward.url", "")
        self.forward_method = self.config.get("forward.method", "POST")
        self.forward_headers = self.config.get("forward.headers", {})
        self.forward_timeout = self.config.get("forward.timeout", 5)
        self.forward_retry = self.config.get("forward.retry", 2)

class PushService:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.push_endpoint = config.get("push.endpoint", "")
        self.push_headers = config.get("push.headers", {})
        self.push_timeout = config.get("push.timeout", 5)

    async def push_reply(self, session_id: str, user_id: str, reply: str):
        if not self.push_endpoint:
            return
        
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "sender": "agent",
            "content": reply,
            "timestamp": int(asyncio.get_event_loop().time())
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url=self.push_endpoint,
                    json=payload,
                    headers=self.push_headers,
                    timeout=self.push_timeout
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                pass

    def update_config(self):
        self.push_endpoint = self.config.get("push.endpoint", "")
        self.push_headers = self.config.get("push.headers", {})
        self.push_timeout = self.config.get("push.timeout", 5)
