import re
import logging
from typing import List, Dict, Any

from ..config import get_config_manager
from ..tasks import TaskExecutor

logger = logging.getLogger(__name__)

class PostGuard:
    def __init__(self):
        self._config = get_config_manager()
        self._task_executor = TaskExecutor()
        self._enabled = self._config.get('security.post_guard.enabled', True)
        
        self._sensitive_patterns = [
            r'\b\d{11}\b',
            r'\b\d{15,18}\b',
            r'\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            r'\b\d{16}\b'
        ]
    
    async def check(self, response: str, user_id: str = "") -> tuple[bool, str, str]:
        if not self._enabled:
            return True, "", response
        
        if self._contains_sensitive_info(response):
            safe_response = self._mask_sensitive_info(response)
            logger.warning("Post-guard masked sensitive info in response")
            return True, "", safe_response
        
        try:
            messages = [
                {
                    'role': 'user',
                    'content': f"请检查以下回复是否安全（不包含角色偏离、指令泄露或违规内容）：\n{response}"
                }
            ]
            
            result = await self._task_executor.execute(
                'post_guard',
                messages,
                user_id=user_id
            )
            
            if 'unsafe' in result.lower() or '违规' in result:
                logger.warning(f"Post-guard flagged response: {result}")
                return False, result, response
            
        except Exception as e:
            logger.error(f"Post-guard check failed: {e}")
        
        return True, "", response
    
    def _contains_sensitive_info(self, text: str) -> bool:
        for pattern in self._sensitive_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _mask_sensitive_info(self, text: str) -> str:
        masked = text
        
        masked = re.sub(r'\b\d{11}\b', '***********', masked)
        masked = re.sub(r'\b\d{15,18}\b', '**********', masked)
        masked = re.sub(r'\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '****-****-****-****', masked)
        masked = re.sub(r'\b\d{16}\b', '****-****-****-****', masked)
        
        return masked
