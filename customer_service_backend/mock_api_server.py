#!/usr/bin/env python3
"""
Mock AI API Server with TUI Interface
用于测试的模拟AI服务，通过TUI提供交互式控制和Agent自动回复
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    print("请安装 rich 库: pip install rich")
    exit(1)


class RequestType(Enum):
    CHAT = "chat"
    EMBEDDING = "embedding"
    COMPLETION = "completion"
    UNKNOWN = "unknown"


@dataclass
class APIRequest:
    id: str
    method: str
    path: str
    headers: Dict[str, str]
    body: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    response: Optional[Dict[str, Any]] = None
    status_code: int = 200
    processing_time: float = 0


class MockResponseBuilder:
    """构建模拟AI响应"""

    @staticmethod
    def build_chat_response(user_input: str, model: str = "mock-gpt-4") -> Dict[str, Any]:
        user_lower = user_input.lower()

        if any(g in user_lower for g in ["你好", "hello", "hi", "嗨"]):
            response_text = "你好！我是模拟AI助手。有什么可以帮助你的吗？"
        elif any(g in user_lower for g in ["帮助", "help", "帮忙", "能做什么"]):
            response_text = "我可以帮你：1) 回答常见问题 2) 提供产品信息 3) 故障排查指导 4) 转接人工客服"
        elif any(g in user_lower for g in ["价格", "费用", "cost", "price"]):
            response_text = "我们的服务价格分为三个档次：基础版免费，专业版99元/月，企业版面议"
        elif any(g in user_lower for g in ["问题", "bug", "错误", "issue", "problem"]):
            response_text = "很抱歉给您带来不便。请描述一下具体的问题现象，我会尽力帮您解决。如果需要转人工客服，请回复转人工。"
        elif any(g in user_lower for g in ["人工", "客服", "人工客服", "真人"]):
            response_text = "好的，我现在为您转接人工客服，请稍候..."
        elif any(g in user_lower for g in ["谢谢", "thanks", "感谢"]):
            response_text = "不客气！很高兴能帮助您。如有其他问题随时联系我。"
        elif any(g in user_lower for g in ["再见", "bye", "结束", "quit"]):
            response_text = "再见！祝您生活愉快！"
        else:
            response_text = f"收到您的消息：{user_input}。请问还有什么需要帮助的吗？"

        return {
            "id": f"chatcmpl-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(user_input),
                "completion_tokens": len(response_text),
                "total_tokens": len(user_input) + len(response_text)
            }
        }

    @staticmethod
    def build_embedding_response(text: str) -> Dict[str, Any]:
        import hashlib
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        import random
        random.seed(seed)

        dimensions = 1536
        vector = [random.uniform(-1, 1) for _ in range(dimensions)]
        norm = sum(x**2 for x in vector) ** 0.5
        vector = [x / norm for x in vector]

        return {
            "object": "list",
            "data": [{
                "object": "embedding",
                "embedding": vector,
                "index": 0
            }],
            "model": "text-embedding-ada-002",
            "usage": {
                "prompt_tokens": len(text),
                "total_tokens": len(text)
            }
        }


class MockAPIServer:
    """Mock API 服务器核心"""

    def __init__(self, port: int = 8080):
        self.port = port
        self.console = Console()
        self.requests: list[APIRequest] = []
        self.server = None
        self.agent_mode = False
        self.stats = {
            "total_requests": 0,
            "chat_requests": 0,
            "embedding_requests": 0,
        }

    def parse_request(self, method: str, path: str, headers: Dict, body: Dict) -> RequestType:
        if "/chat/completions" in path or "/chat" in path:
            return RequestType.CHAT
        elif "/embeddings" in path or "/embedding" in path:
            return RequestType.EMBEDDING
        return RequestType.UNKNOWN

    def handle_request(self, method: str, path: str, headers: Dict, body: Dict) -> tuple[int, Dict]:
        start_time = time.time()
        req_id = f"req-{len(self.requests) + 1}"

        request = APIRequest(
            id=req_id,
            method=method,
            path=path,
            headers=headers,
            body=body
        )

        req_type = self.parse_request(method, path, headers, body)
        response = {"error": "Not found"}
        status = 404

        if req_type == RequestType.CHAT:
            user_input = ""
            if "messages" in body:
                for msg in body["messages"]:
                    if msg.get("role") == "user":
                        user_input = msg.get("content", "")
                        break
            elif "user_input" in body:
                user_input = body["user_input"]

            response = MockResponseBuilder.build_chat_response(user_input)
            status = 200
            self.stats["chat_requests"] += 1

        elif req_type == RequestType.EMBEDDING:
            text = body.get("input", "")
            if isinstance(text, list):
                text = text[0] if text else ""
            response = MockResponseBuilder.build_embedding_response(text)
            status = 200
            self.stats["embedding_requests"] += 1

        self.stats["total_requests"] += 1
        request.response = response
        request.status_code = status
        request.processing_time = time.time() - start_time
        self.requests.append(request)
        return status, response


async def start_http_server(server: MockAPIServer, host: str = "0.0.0.0", port: int = 8080):
    """使用 asyncio 运行简单 HTTP 服务器"""

    async def handle_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            data = await reader.read(8192)
            if not data:
                writer.close()
                await writer.wait_closed()
                return

            text = data.decode('utf-8', errors='replace')
            lines = text.split('\r\n')

            if len(lines) < 1:
                writer.close()
                await writer.wait_closed()
                return

            request_line = lines[0].split(' ')
            if len(request_line) < 3:
                writer.close()
                await writer.wait_closed()
                return

            method = request_line[0]
            path = request_line[1]

            headers = {}
            body_start = 0
            content_length = 0
            for i, line in enumerate(lines[1:], 1):
                if line == '':
                    body_start = i + 1
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
                    if key.strip().lower() == 'content-length':
                        content_length = int(value.strip())

            body = {}
            if body_start > 0 and body_start <= len(lines):
                body_text = '\r\n'.join(lines[body_start:])
                if body_text and content_length > 0:
                    try:
                        body = json.loads(body_text)
                    except:
                        body = {"raw": body_text[:content_length]}

            status_code, response = server.handle_request(method, path, headers, body)

            response_text = json.dumps(response, ensure_ascii=False)
            response_headers = f"HTTP/1.1 {status_code} OK\r\nContent-Type: application/json\r\nContent-Length: {len(response_text)}\r\nConnection: close\r\n\r\n"

            writer.write(response_headers.encode())
            writer.write(response_text.encode())
            await writer.drain()

        except Exception as e:
            print(f"[Error] {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    server.server = await asyncio.start_server(handle_request, host, port)
    print(f"Mock API Server running on http://{host}:{port}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mock AI API Server")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Server port")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--no-tui", action="store_true", help="Disable TUI")
    args = parser.parse_args()

    server = MockAPIServer(port=args.port)
    await start_http_server(server, args.host, args.port)

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass

    server.server.close()
    await server.server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
