import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from ..memory import RedisShortTermMemory, RedisConversationHistory
from ..tasks import TaskExecutor
from ..config import get_config_manager

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    session_id: str
    user_id: str
    user_input: str
    history: List[Dict[str, str]]
    context: str
    decision: str
    response: str
    should_escalate: bool
    error: Optional[str]

class AgentNodes:
    def __init__(
        self,
        memory: RedisShortTermMemory,
        conversation_history: RedisConversationHistory,
        task_executor: TaskExecutor
    ):
        self.memory = memory
        self.conversation_history = conversation_history
        self.task_executor = task_executor
        self.config = get_config_manager()
    
    async def listen(self, state: AgentState) -> AgentState:
        session_id = state['session_id']
        
        history = await self.memory.get_history(session_id)
        
        history_formatted = []
        for msg in history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_formatted.append({'role': role, 'content': content})
        
        state['history'] = history_formatted
        
        return state
    
    async def think(self, state: AgentState) -> AgentState:
        history = state.get('history', [])
        user_input = state['user_input']
        
        history_text = '\n'.join([f"{msg['role']}: {msg['content']}" for msg in history[-6:]])
        
        messages = [
            {
                'role': 'user',
                'content': f"对话历史：\n{history_text}\n\n用户输入：{user_input}"
            }
        ]
        
        try:
            think_prompt = self.config.get('agent.think_prompt', '')
            messages_with_prompt = [
                {'role': 'system', 'content': think_prompt}
            ] + messages
            
            result = await self.task_executor.execute(
                'short_term_plan',
                messages_with_prompt,
                user_id=state['user_id']
            )
            
            import json
            try:
                decision_data = json.loads(result)
                state['decision'] = decision_data.get('decision', 'direct')
            except json.JSONDecodeError:
                if 'rag' in result.lower():
                    state['decision'] = 'rag'
                elif 'escalate' in result.lower():
                    state['decision'] = 'escalate'
                else:
                    state['decision'] = 'direct'
            
        except Exception as e:
            logger.error(f"Think step failed: {e}")
            state['decision'] = 'direct'
        
        return state
    
    async def decide(self, state: AgentState) -> str:
        decision = state.get('decision', 'direct')
        
        escalate_keywords = self.config.get('agent.escalate_keywords', [])
        if any(keyword in state['user_input'] for keyword in escalate_keywords):
            return 'escalate'
        
        return decision
    
    async def act(self, state: AgentState) -> AgentState:
        decision = state.get('decision', 'direct')
        
        if decision == 'escalate':
            state['should_escalate'] = True
        else:
            state['should_escalate'] = False
        
        return state
    
    async def respond(self, state: AgentState) -> AgentState:
        if state.get('should_escalate', False):
            return state
        
        history = state.get('history', [])
        user_input = state['user_input']
        
        history_text = '\n'.join([f"{msg['role']}: {msg['content']}" for msg in history])
        context = state.get('context', '无')
        
        system_prompt = self.config.get('agent.system_prompt_template', '')
        
        messages = [
            {'role': 'system', 'content': system_prompt.format(
                history=history_text or '无',
                context=context,
                user_input=user_input
            )},
            {'role': 'user', 'content': user_input}
        ]
        
        try:
            if len(history) < 2:
                result = await self.task_executor.execute(
                    'simple_response',
                    messages,
                    user_id=state['user_id']
                )
            else:
                result = await self.task_executor.execute(
                    'main_response',
                    messages,
                    user_id=state['user_id']
                )
            
            state['response'] = result
            
        except Exception as e:
            logger.error(f"Respond step failed: {e}")
            state['error'] = str(e)
            state['response'] = self.config.get('agent.response_templates.rejection', '服务暂时不可用')
        
        return state
    
    async def update(self, state: AgentState) -> AgentState:
        if state.get('error'):
            return state
        
        session_id = state['session_id']
        response = state.get('response', '')
        
        user_message = {
            'role': 'user',
            'content': state['user_input']
        }
        assistant_message = {
            'role': 'assistant',
            'content': response
        }
        
        await self.memory.add_messages(session_id, [user_message, assistant_message])
        
        await self.conversation_history.add_messages(session_id, [user_message, assistant_message])
        
        return state
    
    async def post_check(self, state: AgentState) -> AgentState:
        response = state.get('response', '')
        
        if not response:
            return state
        
        try:
            messages = [
                {'role': 'user', 'content': f"请检查以下回复是否安全：\n{response}"}
            ]
            
            check_result = await self.task_executor.execute(
                'post_guard',
                messages,
                user_id=state['user_id']
            )
            
            if 'unsafe' in check_result.lower() or '违规' in check_result:
                escalate_templates = self.config.get('agent.response_templates.escalate', '')
                state['response'] = escalate_templates
                state['should_escalate'] = True
            
        except Exception as e:
            logger.error(f"Post check failed: {e}")
        
        return state

def create_agent_graph(
    memory: RedisShortTermMemory,
    conversation_history: RedisConversationHistory,
    task_executor: TaskExecutor
) -> StateGraph:
    nodes = AgentNodes(memory, conversation_history, task_executor)
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("listen", nodes.listen)
    workflow.add_node("think", nodes.think)
    workflow.add_node("act", nodes.act)
    workflow.add_node("respond", nodes.respond)
    workflow.add_node("post_check", nodes.post_check)
    workflow.add_node("update", nodes.update)
    
    def route_decision(state: AgentState) -> str:
        if state.get('should_escalate', False):
            return 'update'
        return 'think'
    
    workflow.set_entry_point("listen")
    
    workflow.add_edge("listen", "think")
    workflow.add_edge("think", "act")
    workflow.add_edge("act", "decide")
    workflow.add_conditional_edges(
        "act",
        lambda state: 'respond' if not state.get('should_escalate', False) else 'update',
        {
            True: 'update',
            False: 'respond'
        }
    )
    workflow.add_edge("respond", "post_check")
    workflow.add_edge("post_check", "update")
    workflow.add_edge("update", END)
    
    return workflow.compile()
