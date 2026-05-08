import logging
import asyncio
from typing import List, Dict, Any, Optional
from functools import lru_cache

from ..config import get_config_manager
from ..providers import get_provider_manager
from .builtin import RuleBasedFallback

logger = logging.getLogger(__name__)

class TaskExecutor:
    def __init__(self):
        self._config = get_config_manager()
        self._provider_manager = get_provider_manager()
        self._rule_fallback = RuleBasedFallback()
    
    async def execute(
        self, 
        task_name: str, 
        messages: List[Dict[str, str]], 
        user_id: str = "",
        **params
    ) -> str:
        task_config = self._config.get(f'tasks.{task_name}')
        if not task_config:
            raise ValueError(f"Task not configured: {task_name}")
        
        model_id = task_config.get('model')
        fallback = task_config.get('fallback')
        timeout = task_config.get('timeout', 30)
        
        if not model_id:
            raise ValueError(f"Model not configured for task: {task_name}")
        
        try:
            provider, model_name, model_config = self._provider_manager.get_model(model_id)
            
            merged_messages = []
            if user_id:
                merged_messages.append({
                    "role": "system",
                    "content": f"用户ID: {user_id}"
                })
            merged_messages.extend(messages)
            
            merged_params = {**model_config, **params}
            
            result = await asyncio.wait_for(
                provider.chat_completion(merged_messages, model_name, **merged_params),
                timeout=timeout
            )
            
            logger.info(f"Task {task_name} completed successfully with model {model_id}")
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_name} timed out with model {model_id}")
            if fallback:
                return await self._handle_fallback(task_name, fallback, messages, user_id)
            raise
        
        except Exception as e:
            logger.error(f"Task {task_name} failed with model {model_id}: {e}")
            if fallback:
                return await self._handle_fallback(task_name, fallback, messages, user_id)
            raise
    
    async def _handle_fallback(
        self, 
        task_name: str, 
        fallback: str, 
        messages: List[Dict[str, str]],
        user_id: str = ""
    ) -> str:
        logger.info(f"Using fallback {fallback} for task {task_name}")
        
        if fallback == 'rule_based':
            return await self._rule_fallback.execute(task_name, messages)
        
        if '/' in fallback:
            try:
                provider, model_name, model_config = self._provider_manager.get_model(fallback)
                
                merged_messages = []
                if user_id:
                    merged_messages.append({
                        "role": "system", 
                        "content": f"用户ID: {user_id}"
                    })
                merged_messages.extend(messages)
                
                return await provider.chat_completion(merged_messages, model_name, **model_config)
            except Exception as e:
                logger.error(f"Fallback model {fallback} also failed: {e}")
                raise
        
        raise ValueError(f"Unknown fallback type: {fallback}")
    
    async def execute_stream(
        self, 
        task_name: str, 
        messages: List[Dict[str, str]], 
        user_id: str = "",
        **params
    ):
        task_config = self._config.get(f'tasks.{task_name}')
        if not task_config:
            raise ValueError(f"Task not configured: {task_name}")
        
        model_id = task_config.get('model')
        timeout = task_config.get('timeout', 30)
        
        if not model_id:
            raise ValueError(f"Model not configured for task: {task_name}")
        
        provider, model_name, model_config = self._provider_manager.get_model(model_id)
        
        merged_messages = []
        if user_id:
            merged_messages.append({
                "role": "system",
                "content": f"用户ID: {user_id}"
            })
        merged_messages.extend(messages)
        
        merged_params = {**model_config, **params}
        
        try:
            async for chunk in provider.stream_chat_completion(merged_messages, model_name, **merged_params):
                yield chunk
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_name} timed out with model {model_id}")
            raise
        except Exception as e:
            logger.error(f"Task {task_name} failed with model {model_id}: {e}")
            raise
    
    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        tasks_config = self._config.get('tasks', {})
        result = {}
        for task_name, task_config in tasks_config.items():
            result[task_name] = {
                'model': task_config.get('model'),
                'fallback': task_config.get('fallback'),
                'timeout': task_config.get('timeout', 30)
            }
        return result
    
    async def update_task_model(self, task_name: str, model_id: str) -> bool:
        try:
            self._config.set(f'tasks.{task_name}.model', model_id)
            logger.info(f"Updated task {task_name} to use model {model_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_name}: {e}")
            return False

@lru_cache(maxsize=1)
def get_task_executor() -> TaskExecutor:
    return TaskExecutor()
