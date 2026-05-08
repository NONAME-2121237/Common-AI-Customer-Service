import logging
from typing import Dict, Any, Optional

from .nodes import create_agent_graph, AgentState
from ..memory import RedisShortTermMemory, RedisConversationHistory, SessionManager
from ..tasks import TaskExecutor

logger = logging.getLogger(__name__)

class CustomerServiceAgent:
    def __init__(
        self,
        memory: RedisShortTermMemory,
        conversation_history: RedisConversationHistory,
        task_executor: TaskExecutor
    ):
        self.memory = memory
        self.conversation_history = conversation_history
        self.task_executor = task_executor
        self.graph = create_agent_graph(memory, conversation_history, task_executor)
    
    async def process(
        self,
        session_id: str,
        user_id: str,
        user_input: str
    ) -> Dict[str, Any]:
        initial_state: AgentState = {
            'session_id': session_id,
            'user_id': user_id,
            'user_input': user_input,
            'history': [],
            'context': '',
            'decision': 'direct',
            'response': '',
            'should_escalate': False,
            'error': None
        }
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            return {
                'response': final_state.get('response', ''),
                'should_escalate': final_state.get('should_escalate', False),
                'error': final_state.get('error'),
                'session_id': session_id,
                'user_id': user_id
            }
        except Exception as e:
            logger.error(f"Agent processing failed: {e}")
            return {
                'response': '处理您的请求时出现错误，请稍后重试。',
                'should_escalate': False,
                'error': str(e),
                'session_id': session_id,
                'user_id': user_id
            }
