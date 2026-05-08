import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RuleBasedFallback:
    def __init__(self):
        self._greeting_patterns = [
            r'^你好',
            r'^您好',
            r'^hi',
            r'^hello',
            r'^嗨',
            r'^hey'
        ]
        
        self._greeting_responses = [
            "您好！有什么可以帮助您的吗？",
            "您好，请问有什么问题需要咨询？",
            "您好，欢迎使用客服服务。"
        ]
        
        self._thanks_patterns = [
            r'谢谢',
            r'感谢',
            r'多谢',
            r'thanks'
        ]
        
        self._thanks_responses = [
            "不客气！还有其他问题吗？",
            "很高兴能帮助到您！"
        ]
    
    async def execute(self, task_name: str, messages: List[Dict[str, str]]) -> str:
        if task_name == 'pre_guard':
            return await self._guard_check(messages)
        elif task_name == 'simple_response':
            return await self._simple_response(messages)
        else:
            return await self._default_response(messages)
    
    async def _guard_check(self, messages: List[Dict[str, str]]) -> str:
        last_message = messages[-1]['content'] if messages else ''
        
        dangerous_patterns = [
            r'system\s*:',
            r'ignore\s*previous',
            r'你是一个.*角色',
            r'忘掉.*之前'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, last_message, re.IGNORECASE):
                return "unsafe"
        
        return "safe"
    
    async def _simple_response(self, messages: List[Dict[str, str]]) -> str:
        last_message = messages[-1]['content'] if messages else ''
        
        for pattern in self._greeting_patterns:
            if re.search(pattern, last_message, re.IGNORECASE):
                import random
                return random.choice(self._greeting_responses)
        
        for pattern in self._thanks_patterns:
            if re.search(pattern, last_message, re.IGNORECASE):
                import random
                return random.choice(self._thanks_responses)
        
        return "您好，请问有什么可以帮助您的？"
    
    async def _default_response(self, messages: List[Dict[str, str]]) -> str:
        return "抱歉，我暂时无法处理您的请求，请稍后重试。"
