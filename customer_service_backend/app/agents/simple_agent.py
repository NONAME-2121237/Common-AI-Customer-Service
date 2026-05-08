from typing import Dict, Any, List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)


class CustomerServiceAgent:
    def __init__(self, memory, conversation_history, task_executor):
        self.memory = memory
        self.conversation_history = conversation_history
        self.task_executor = task_executor

    async def process(self, session_id: str, user_id: str, user_input: str) -> Dict[str, Any]:
        await self.conversation_history.add_message(
            session_id=session_id,
            role="user",
            content=user_input
        )

        await self.memory.add(
            session_id=session_id,
            content=user_input,
            role="user"
        )

        try:
            response = await self._call_ai(session_id, user_input)
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            response = self._get_default_response(user_input)

        await self.conversation_history.add_message(
            session_id=session_id,
            role="assistant",
            content=response
        )

        await self.memory.add(
            session_id=session_id,
            content=response,
            role="assistant"
        )

        should_escalate = any(kw in user_input for kw in ["人工", "转人工", "客服", "help"])

        return {
            "response": response,
            "session_id": session_id,
            "should_escalate": should_escalate
        }

    async def _call_ai(self, session_id: str, user_input: str) -> str:
        history = await self.conversation_history.get_history(session_id, limit=10)
        messages = [{"role": "system", "content": "你是智能客服助手，请简洁专业地回答用户问题。"}]
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_input})

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    "http://localhost:8080/chat/completions",
                    json={"model": "mock-gpt-4", "messages": messages}
                )
                data = resp.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"Mock API call failed: {e}")

        return self._get_default_response(user_input)

    def _get_default_response(self, user_input: str) -> str:
        user_lower = user_input.lower()
        if any(g in user_lower for g in ["你好", "hello", "hi", "嗨"]):
            return "你好！有什么可以帮助你的吗？"
        elif any(g in user_lower for g in ["帮助", "help", "帮忙"]):
            return "我可以帮你回答问题、转接人工服务或提供产品信息。"
        elif any(g in user_lower for g in ["价格", "费用"]):
            return "我们的服务价格透明，欢迎咨询。"
        elif any(g in user_lower for g in ["人工", "转人工"]):
            return "好的，正在为您转接人工客服..."
        elif any(g in user_lower for g in ["谢谢", "thanks"]):
            return "不客气！祝您生活愉快！"
        else:
            return f"收到您的消息：{user_input}。请问还有什么需要帮助的吗？"
