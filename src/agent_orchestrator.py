from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage
from config_manager import ConfigManager
from task_executor import TaskExecutor

class AgentState(TypedDict):
    user_id: str
    session_id: str
    message: str
    history: List[Dict[str, str]]
    decision: Optional[str]
    response: Optional[str]
    transfer: bool
    interrupt: bool

class AgentOrchestrator:
    def __init__(self, config: ConfigManager, task_executor: TaskExecutor):
        self.config = config
        self.task_executor = task_executor
        self.max_iterations = config.get("app.max_agent_iterations", 5)
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        
        graph.add_node("listen", self._listen)
        graph.add_node("classify", self._classify)
        graph.add_node("think", self._think)
        graph.add_node("decide", self._decide)
        graph.add_node("act", self._act)
        graph.add_node("respond", self._respond)
        graph.add_node("post_check", self._post_check)
        graph.add_node("update", self._update)
        graph.add_node("check_interrupt", self._check_interrupt)
        
        graph.add_edge("listen", "classify")
        graph.add_edge("classify", "think")
        graph.add_edge("think", "decide")
        graph.add_edge("decide", "act")
        graph.add_edge("act", "respond")
        graph.add_edge("respond", "post_check")
        graph.add_edge("post_check", "update")
        graph.add_edge("update", "check_interrupt")
        graph.add_edge("check_interrupt", END)
        
        graph.set_entry_point("listen")
        
        return graph.compile()

    async def _listen(self, state: AgentState) -> Dict[str, Any]:
        return {"message": state["message"]}

    async def _classify(self, state: AgentState) -> Dict[str, Any]:
        try:
            result = await self.task_executor.execute(
                "intent_classify",
                message=state["message"]
            )
            return {"intent": result.get("intent", "")}
        except Exception:
            return {"intent": "unknown"}

    async def _think(self, state: AgentState) -> Dict[str, Any]:
        history = state["history"]
        history.append({"role": "user", "content": state["message"]})
        
        result = await self.task_executor.execute(
            "short_term_plan",
            messages=history
        )
        return {"decision": result.get("decision", "direct")}

    async def _decide(self, state: AgentState) -> Dict[str, Any]:
        decision = state.get("decision", "direct")
        return {"decision": decision}

    async def _act(self, state: AgentState) -> Dict[str, Any]:
        decision = state.get("decision", "direct")
        
        if decision == "escalate":
            return {"response": "TRANSFER_TO_HUMAN", "transfer": True}
        
        history = state["history"]
        history.append({"role": "user", "content": state["message"]})
        
        task_name = "main_response" if decision == "direct" else "simple_response"
        result = await self.task_executor.execute(
            task_name,
            messages=history
        )
        
        return {"response": result.get("response", ""), "transfer": False}

    async def _respond(self, state: AgentState) -> Dict[str, Any]:
        response = state.get("response", "")
        transfer = state.get("transfer", False)
        
        if response == "TRANSFER_TO_HUMAN":
            return {"response": "您的问题已转接人工客服，请稍候。", "transfer": True}
        
        return {"response": response, "transfer": transfer}

    async def _post_check(self, state: AgentState) -> Dict[str, Any]:
        response = state.get("response", "")
        transfer = state.get("transfer", False)
        
        if transfer:
            return {"safe": True, "transfer": True}
        
        result = await self.task_executor.execute(
            "post_guard",
            response=response
        )
        
        if not result.get("safe", True):
            return {
                "response": "抱歉，我无法回答这个问题，请联系人工客服。",
                "transfer": True,
                "safe": False
            }
        
        return {"safe": True, "transfer": False}

    async def _update(self, state: AgentState) -> Dict[str, Any]:
        response = state.get("response", "")
        history = state.get("history", [])
        transfer = state.get("transfer", False)
        
        if response and not transfer:
            history.append({"role": "assistant", "content": response})
        
        return {"history": history}

    async def _check_interrupt(self, state: AgentState) -> Dict[str, Any]:
        return {"interrupt": state.get("interrupt", False)}

    async def run(self, user_id: str, session_id: str, message: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
        state = {
            "user_id": user_id,
            "session_id": session_id,
            "message": message,
            "history": history.copy(),
            "decision": None,
            "response": None,
            "transfer": False,
            "interrupt": False
        }
        
        result = await self.graph.ainvoke(state)
        
        return {
            "response": result.get("response", ""),
            "transfer": result.get("transfer", False),
            "history": result.get("history", [])
        }
