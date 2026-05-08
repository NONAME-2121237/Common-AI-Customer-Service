import logging
import httpx
from typing import Dict, Any, List, Optional

from ..config import get_config_manager

logger = logging.getLogger(__name__)

class MessageForwarder:
    def __init__(self):
        self._config = get_config_manager()
        self._transfer_config = self._config.get('routing.transfer', {})
    
    async def forward_message(
        self,
        session_id: str,
        user_id: str,
        message: str,
        conversation_history: List[Dict[str, Any]] = None
    ) -> bool:
        target_url = self._transfer_config.get('default_target_url', '')
        if not target_url:
            logger.error("Transfer target URL not configured")
            return False
        
        method = self._transfer_config.get('method', 'POST')
        headers = self._transfer_config.get('headers', {'Content-Type': 'application/json'})
        timeout = self._transfer_config.get('timeout', 5)
        retry = self._transfer_config.get('retry', 1)
        
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'message': message,
            'conversation_history': conversation_history or []
        }
        
        for attempt in range(retry + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method == 'POST':
                        response = await client.post(target_url, json=payload, headers=headers)
                    else:
                        response = await client.get(target_url, params=payload, headers=headers)
                    
                    response.raise_for_status()
                    logger.info(f"Message forwarded successfully to {target_url}")
                    return True
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error forwarding message (attempt {attempt + 1}): {e.response.status_code}")
                if attempt >= retry:
                    return False
                    
            except Exception as e:
                logger.error(f"Error forwarding message (attempt {attempt + 1}): {e}")
                if attempt >= retry:
                    return False
        
        return False
    
    async def forward_with_full_context(
        self,
        session_id: str,
        user_id: str,
        message: str,
        conversation_history: List[Dict[str, Any]],
        short_term_memory: List[Dict[str, Any]] = None
    ) -> bool:
        target_url = self._transfer_config.get('default_target_url', '')
        if not target_url:
            logger.error("Transfer target URL not configured")
            return False
        
        headers = self._transfer_config.get('headers', {'Content-Type': 'application/json'})
        timeout = self._transfer_config.get('timeout', 5)
        
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'current_message': message,
            'conversation_history': conversation_history,
            'short_term_memory': short_term_memory or []
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(target_url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"Message with full context forwarded successfully")
                return True
        except Exception as e:
            logger.error(f"Error forwarding message with full context: {e}")
            return False
