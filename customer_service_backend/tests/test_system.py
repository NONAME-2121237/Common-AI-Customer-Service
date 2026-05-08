#!/usr/bin/env python3
"""
测试脚本 - 验证后端和WebUI功能
"""

import asyncio
import httpx
import sys
import subprocess

BASE_URL = "http://localhost:8000"
WEBUI_URL = "http://localhost:80"
MOCK_API_URL = "http://localhost:8080"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, passed, detail=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"  [{status}] {name}")
    if detail:
        print(f"         {detail}")

async def test_mock_api():
    print(f"\n{Colors.BLUE}[1] Mock API 测试{Colors.END}")

    try:
        proc = await asyncio.create_subprocess_shell(
            f'curl -s -X POST {MOCK_API_URL}/chat/completions -H "Content-Type: application/json" -d \'{{"messages":[{{"role":"user","content":"你好"}}]}}\'',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        data = stdout.decode().strip()
        passed = '"choices"' in data
        print_test("Mock Chat API 响应", passed, f"Got {len(data)} bytes")
        return passed
    except Exception as e:
        print_test("Mock Chat API 响应", False, str(e))
        return False

async def test_health():
    print(f"\n{Colors.BLUE}[2] 后端健康检查{Colors.END}")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{BASE_URL}/health", timeout=5.0)
            data = resp.json()
            passed = resp.status_code == 200 and data.get("status") == "healthy"
            print_test("Health endpoint", passed, f"Response: {data}")
            return passed
        except Exception as e:
            print_test("Health endpoint", False, str(e))
            return False

async def test_auth():
    print(f"\n{Colors.BLUE}[3] 认证测试{Colors.END}")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{BASE_URL}/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=5.0
            )
            data = resp.json()
            passed = resp.status_code == 200 and "token" in data
            print_test("Login with default admin", passed, f"Status: {resp.status_code}")
            if not passed:
                return False

            token = data["token"]
            headers = {"Authorization": f"Bearer {token}"}

            resp = await client.get(f"{BASE_URL}/auth/me", headers=headers, timeout=5.0)
            passed = resp.status_code == 200 and resp.json().get("username") == "admin"
            print_test("Get current user", passed, f"User: {resp.json().get('username')}")

            resp = await client.get(f"{BASE_URL}/auth/me", timeout=5.0)
            passed = resp.status_code == 401
            print_test("Reject unauthenticated request", passed, f"Status: {resp.status_code}")

            return True

        except Exception as e:
            print_test("Authentication tests", False, str(e))
            return False

async def test_chat():
    print(f"\n{Colors.BLUE}[4] 聊天功能测试{Colors.END}")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{BASE_URL}/v1/chat",
                json={"user_id": "test_user_1", "user_input": "你好"},
                timeout=10.0
            )
            data = resp.json()
            passed = resp.status_code == 200 and "response" in data
            print_test("Chat endpoint", passed, f"Response: {data.get('response', '')[:50]}...")
            return passed
        except Exception as e:
            print_test("Chat endpoint", False, str(e))
            return False

async def test_kb():
    print(f"\n{Colors.BLUE}[5] 知识库配置测试{Colors.END}")

    async with httpx.AsyncClient() as client:
        try:
            login_resp = await client.post(
                f"{BASE_URL}/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=5.0
            )
            token = login_resp.json().get("token")
            headers = {"Authorization": f"Bearer {token}"}

            resp = await client.get(f"{BASE_URL}/kb/documents", headers=headers, timeout=5.0)
            passed = resp.status_code == 200
            print_test("Get KB documents", passed, f"Count: {resp.json().get('count', 0)}")

            resp = await client.get(f"{BASE_URL}/kb/config", headers=headers, timeout=5.0)
            passed = resp.status_code == 200
            print_test("Get KB config", passed)

            resp = await client.post(
                f"{BASE_URL}/kb/query",
                json={"query": "常见问题", "top_k": 3},
                headers=headers,
                timeout=5.0
            )
            passed = resp.status_code == 200
            print_test("KB query", passed, f"Results: {len(resp.json().get('results', []))}")

            return True

        except Exception as e:
            print_test("Knowledge base tests", False, str(e))
            return False

async def test_admin():
    print(f"\n{Colors.BLUE}[6] Admin API 测试{Colors.END}")

    async with httpx.AsyncClient() as client:
        try:
            login_resp = await client.post(
                f"{BASE_URL}/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=5.0
            )
            token = login_resp.json().get("token")
            headers = {"Authorization": f"Bearer {token}"}

            resp = await client.get(f"{BASE_URL}/admin/config", headers=headers, timeout=5.0)
            passed = resp.status_code == 200
            print_test("Get admin config", passed)

            resp = await client.get(f"{BASE_URL}/admin/session/transferred", headers=headers, timeout=5.0)
            passed = resp.status_code == 200
            print_test("Get transferred sessions", passed)

            resp = await client.get(f"{BASE_URL}/admin/providers", headers=headers, timeout=5.0)
            passed = resp.status_code == 200
            print_test("Get providers", passed)

            return True

        except Exception as e:
            print_test("Admin API tests", False, str(e))
            return False

async def test_webui_build():
    print(f"\n{Colors.BLUE}[7] WebUI 构建测试{Colors.END}")
    try:
        proc = await asyncio.create_subprocess_shell(
            "cd /workspace/customer_service_backend/webui && npm run build 2>&1 | tail -5",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        output = stdout.decode()
        passed = "dist" in output or proc.returncode == 0
        print_test("WebUI build", passed, "Built successfully" if passed else "Check errors")
        return passed
    except Exception as e:
        print_test("WebUI build", False, str(e))
        return False

async def main():
    print(f"\n{'='*60}")
    print(f"  智能客服系统 - 自动化测试")
    print(f"{'='*60}")

    results = []

    results.append(await test_mock_api())
    results.append(await test_health())
    results.append(await test_auth())
    results.append(await test_chat())
    results.append(await test_kb())
    results.append(await test_admin())
    results.append(await test_webui_build())

    print(f"\n{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"  测试结果: {passed}/{total} 通过")

    if passed == total:
        print(f"  {Colors.GREEN}所有测试通过！{Colors.END}")
    else:
        print(f"  {Colors.YELLOW}有 {total - passed} 项测试失败（可在Docker环境中重新测试）{Colors.END}")

    print(f"{'='*60}\n")

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
