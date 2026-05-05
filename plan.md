## 1. 项目定位

构建一个**生产级智能客服后端**，具备：

- **低成本高可控**：按任务分配不同规模模型（小模型处理意图/安全，大模型处理核心回复）。
- **多供应商兼容**：同一模型可通过多组 `(base_url, api_key)` 挂载不同账户或服务商，支持 OpenAI 兼容、Anthropic、Google Vertex 等协议。
- **会话转接/人工介入**：Agent 可主动转接，转接期间消息路由到外部接口，同时**清空短期记忆并冻结记忆写入**，保证人工对话不被记录、机器人重新接手时上下文干净。
- **短期记忆凋落**：按时间和重要性自动淘汰低价值消息，严格控制上下文长度。
- **安全审查**：输入输出双重检测，防止注入与角色越狱。
- **配置驱动 + 热重载**：所有可变参数通过 YAML 管理，修改后无需重启。
- **管理 API**：独立本机端口，供呈现模块查看/修改配置、会话状态、日志、释放会话等。

---

## 2. 整体架构

### 2.1 组件图

```
[客户端/前端] ──► 主 API (8000) ──► Agent (LangGraph) ──► 任务执行器 ──► 供应商管理器 ──► 外部 AI API
                   │                       │                 │
                   │                       ├── 短期记忆(Redis)
                   │                       ├── 知识库检索(Dify+Qdrant)
                   │                       ├── 安全审查
                   │                       └── 转接路由
                   │
                   └── 管理 API (8001) ◄── 呈现模块(本地)
```

### 2.2 核心流程

1. 用户请求 `POST /v1/chat {session_id, user_input}`。
2. 检查会话路由状态：
   - 若为 `transferred`：转发消息到外部人工接口；不记录记忆、不调用 Agent。
   - 若为 `active`：进入 Agent 处理。
3. Agent 流程：
   - 加载短期记忆（最近 `recall_limit` 条）。
   - 前置安全审查（若拒绝则返回固定话术）。
   - 意图分类（可选，小模型）。
   - 短期规划（小模型，输出决策 `direct|rag|escalate`）。
   - 若决策为 `rag`，检索知识库获取片段。
   - 生成回复（主回复用大模型，简单回复用小模型或模板）。
   - 后置安全审查（若违规则替换为转接话术）。
   - 保存本轮对话到短期记忆（自动触发凋落整理）。
   - 检查是否有输入打断（Redis 标志位），若有则重置并重试。
4. 若 Agent 调用 `transfer_to_human` 工具：
   - 清空该会话的短期记忆。
   - 设置状态为 `transferred`，标记 `memory_frozen=true`。
   - 返回“正在转接”提示。
5. 外部人工系统处理完毕后，可通过管理 API `POST /admin/session/release` 将状态重置回 `active`，记忆为空（从头开始）。

---

## 3. 配置管理（热重载）

### 3.1 配置文件结构

`config.yaml` 示例（核心部分，完整见附录）：

```yaml
app:
  name: "智能客服后端"
  max_agent_iterations: 5

providers:                       # 供应商分组
  - id: deepseek_main
    type: openai_compatible
    base_url: "https://api.deepseek.com/v1"
    api_key: ${DEEPSEEK_KEY}
    models:
      - name: deepseek-chat
      - name: deepseek-reasoner

models:                          # 全局模型别名
  flash: "deepseek_main/deepseek-chat"
  pro: "deepseek_main/deepseek-reasoner"

tasks:                           # 任务 → 模型绑定
  pre_guard:    { model: "safety", fallback: rule_based }
  intent_classify: { model: "cheap" }
  short_term_plan: { model: "flash" }
  main_response: { model: "pro" }
  simple_response: { model: "flash" }
  post_guard:   { model: "safety" }

memory:
  short_term:
    provider: "redis_score"
    config:
      storage_limit: 30          # 总消息条数上限
      recall_limit: 6            # 每次加载给 LLM 的消息数
      max_age_seconds: 1800      # 超过此时间进入凋落候补
      scoring:
        importance_weights:
          has_order_number: 5
          requested_remember: 10

routing:
  transfer:
    enabled: true
    default_target_url: "https://human-support.example.com/webhook"
    method: "POST"
    headers: { "Content-Type": "application/json" }
    timeout: 5
    auto_release_seconds: 600     # 无消息超时自动释放
    clear_memory_on_transfer: true
    freeze_memory_during_transfer: true

admin:
  api_key: ""                     # 留空则无认证（仅本机）
  log_file: "logs/app.log"
```

### 3.2 ConfigManager

- 单例，加载 YAML，支持 `${ENV_VAR}` 替换。
- `get(path)` 点号路径取值。
- `save_config(updates)` 合并写入，保留注释。
- `watch(path, callback)` 注册热重载回调。
- 文件监控自动 `hot_reload()`。

---

## 4. 供应商与模型管理

### 4.1 Provider 抽象

```python
class Provider(ABC):
    async def chat_completion(messages, model, **params) -> str
    async def stream_chat_completion(...) -> AsyncIterator[str]
    async def health_check() -> bool
```

### 4.2 内置实现

- `OpenAICompatibleProvider`（支持 DeepSeek, OpenAI, Groq, vLLM, Ollama）
- `AnthropicProvider`
- `GoogleVertexProvider`（可选）

### 4.3 ProviderManager

- 根据 `providers` 配置创建实例，挂载多个模型，模型 ID 格式 `{provider_id}/{model_name}`。
- 支持全局别名（`models` 段）。
- `get_model(model_id)` 返回 `(Provider, real_model_name, model_config)`。
- 监听配置变更，热重载时重建所有 Provider 实例。

---

## 5. 任务分级与执行器

### 5.1 任务定义

每个任务绑定一个模型 ID，可配置超时、降级。

### 5.2 TaskExecutor

```python
async def execute(task_name: str, messages: List[Dict], **params) -> str
```

- 读取 `tasks.{task_name}` 获取模型 ID。
- 通过 `ProviderManager.get_model` 获取 Provider。
- 调用 `provider.chat_completion`，合并参数。
- 处理超时，若失败可降级到备用模型或规则。

### 5.3 标准任务列表

| 任务 | 用途 | 推荐模型 |
|------|------|----------|
| `pre_guard` | 输入安全检测 | 小模型（如 Llama Guard） |
| `intent_classify` | 意图分类 | 7B 模型 |
| `short_term_plan` | 决策规划 | 7B~13B 模型 |
| `main_response` | 复杂回复 | 671B MoE（如 DeepSeek） |
| `simple_response` | 简单回复 | 小模型或模板 |
| `post_guard` | 输出安全检测 | 同 pre_guard |

---

## 6. 短期记忆（带凋落）

### 6.1 存储结构

Redis 存储 JSON 数组，每条消息包含：

```json
{
  "role": "user|assistant",
  "content": "文本",
  "timestamp": 1712345678.123,
  "importance_score": 6.5,
  "metadata": { "has_order_number": true }
}
```

### 6.2 凋落算法

- 每次 `add_messages` 后，若总条数 > `storage_limit` 或存在消息年龄 > `max_age_seconds`，触发整理。
- 计算每条消息的保留分数：  
  `score = time_factor * 0.4 + (importance_score/10) * 0.6`  
  时间因子：年龄 < `max_age_seconds` 时线性衰减（1 → 0.5），超过后继续衰减至 0.1。
- 按分数升序排序，丢弃分数最低的直至 ≤ `storage_limit`。
- 保留按时间正序的最终列表。

### 6.3 重要性评分规则

- 通过规则（正则匹配订单号、关键词“请记住”等）或调用小模型计算，分值 0~10。
- 可配置权重（见 `scoring.importance_weights`）。

### 6.4 记忆冻结（转接时）

- 当会话状态为 `transferred` 且 `memory_frozen=true` 时：
  - `add_messages` 直接返回（不写入）。
  - `get_history` 返回空列表（因为已清空且冻结）。
- 转接时同时执行 `reset`（清空）并设置冻结标志。

---

## 7. 会话转接与路由

### 7.1 会话状态（Redis）

Key: `chat:session:{session_id}:route_state`

```json
{
  "status": "active" | "transferred",
  "transferred_at": 1712345678,
  "auto_release_at": 1712346278,
  "reason": "agent_request",
  "memory_frozen": true,
  "last_active": 1712345678
}
```

### 7.2 Agent 转接工具

在 `act` 节点注册工具 `transfer_to_human`，调用时：

- 清空短期记忆（`memory.reset(session_id)`）。
- 设置状态为 `transferred`，`memory_frozen=true`。
- 返回固定提示“正在为您转接人工客服…”。

### 7.3 主 API 路由逻辑

```python
state = await get_route_state(session_id)
if state and state.status == "transferred":
    if now - state.last_active > auto_release_seconds:
        await release_session(session_id)   # 重置为 active
    else:
        await forward_to_external(session_id, user_input)
        return {"reply": "您当前在人工客服，请稍候"}
# 否则正常 Agent 处理
```

### 7.4 自动释放

- 每次用户请求时检查 `last_active` 与配置 `auto_release_seconds`。
- 超时后调用 `release_session`：状态改为 `active`，清除 `memory_frozen`，但不恢复记忆（已清空）。

### 7.5 手动释放（管理 API）

`POST /admin/session/release`  
可选参数 `clear_memory`（默认 false，但转接时已清空，可直接复位状态）。

---

## 8. 知识库检索

- 使用 **Dify** 低代码管理界面，运营人员上传文档、切片。
- 后端通过 Dify API 检索，返回 `top_k` 片段。
- 若 Dify 不可用，可配置直接访问 Qdrant。

---

## 9. 安全审查

### 9.1 前置审查

- 调用 `pre_guard` 任务（小模型或规则）。
- 检出注入/越狱 → 返回 `response_templates.rejection`，终止流程。

### 9.2 后置审查

- 调用 `post_guard` 任务。
- 检出角色偏离/指令泄露 → 替换为转接话术。

### 9.3 规则降级

当模型不可用时使用正则表达式（高危关键词过滤）。

---

## 10. Agent 编排（LangGraph）

### 10.1 节点列表

| 节点 | 功能 |
|------|------|
| `listen` | 加载记忆，前置审查 |
| `classify` | 意图识别（可选） |
| `think` | 规划决策（调用 `short_term_plan` 任务） |
| `decide` | 规则覆盖（关键词、骚扰） |
| `act` | 执行工具（RAG 检索/转接） |
| `respond` | 生成回复（调用 `main_response` 或 `simple_response`） |
| `post_check` | 后置审查 |
| `update` | 保存记忆（若未冻结） |
| `check_interrupt` | 检查是否有新输入打断 |

### 10.2 输入打断

- 使用 Redis 存储 `interrupt:{session_id}` 和 `interrupt_count`。
- `check_interrupt` 节点若检测到新消息且未超过最大次数，则重置状态并跳回 `listen`。

---

## 11. 管理 API（端口 8001，仅 127.0.0.1）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/config` | 获取脱敏配置 |
| PUT | `/admin/config` | 更新扁平配置（如 `tasks.main_response.model=xxx`） |
| GET | `/admin/config/raw` | 获取原始 YAML |
| PUT | `/admin/config/raw` | 整体替换 YAML |
| GET | `/admin/providers` | 列出供应商及模型 |
| GET | `/admin/models` | 列出所有模型 ID 和别名 |
| GET | `/admin/tasks` | 查看任务-模型绑定 |
| POST | `/admin/tasks/{task}/model` | 修改任务模型 |
| GET | `/admin/components/status` | 组件健康检查 |
| POST | `/admin/reboot/component` | 重启组件（如 provider_manager） |
| GET | `/admin/sessions/transferred` | 列出所有转接中的会话 |
| POST | `/admin/session/release` | 释放会话（重置为 active） |
| POST | `/admin/session/transfer` | 手动转接并清空记忆 |
| POST | `/admin/session/clear` | 清空会话短期记忆 |
| POST | `/admin/session/prune` | 手动触发记忆整理 |
| GET | `/admin/logs` | 获取日志 |
| POST | `/admin/logs/level` | 动态调整日志级别 |

---

## 12. 项目目录结构

```
customer_service_backend/
├── app/
│   ├── main.py                     # 主 API
│   ├── admin_main.py               # 管理 API
│   ├── config/
│   │   ├── loader.py               # ConfigManager
│   │   ├── hot_reloader.py
│   │   └── models.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── openai_compatible.py
│   │   ├── anthropic.py
│   │   └── manager.py
│   ├── tasks/
│   │   ├── executor.py
│   │   └── builtin.py
│   ├── agents/
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   └── router.py
│   ├── memory/
│   │   ├── base.py
│   │   └── redis_score.py          # 带凋落与冻结记忆
│   ├── security/
│   │   ├── pre_guard.py
│   │   └── post_guard.py
│   ├── knowledge/
│   │   └── retriever.py
│   ├── routing/
│   │   ├── state.py                # 会话状态管理
│   │   └── forwarder.py            # 转发到外部接口
│   ├── admin/
│   │   └── router.py
│   └── utils/
│       ├── logger.py
│       └── helpers.py
├── config.yaml
├── requirements.txt
└── run.py
```

---

## 13. 开发优先级（建议）

1. 配置管理器 + 热重载
2. 供应商管理器（OpenAI 兼容优先）和 TaskExecutor
3. 短期记忆（基本 FIFO） + Redis
4. Agent 基础循环（无工具、无知识库）
5. 安全审查模块（前置+后置）
6. 知识库检索
7. 记忆凋落算法 + 重要性评分
8. 会话转接状态 + 消息路由 + 转接工具
9. 管理 API（配置修改、会话释放、日志）
10. 完整集成与压力测试

---

## 14. 附录：完整 config.yaml 示例

```yaml
app:
  name: "智能客服后端"
  debug: false
  max_agent_iterations: 5

providers:
  - id: deepseek_main
    type: openai_compatible
    base_url: "https://api.deepseek.com/v1"
    api_key: ${DEEPSEEK_KEY}
    timeout: 30
    models:
      - name: deepseek-chat
        default_params: { temperature: 0.7, max_tokens: 2048 }
      - name: deepseek-reasoner
        default_params: { temperature: 0.3, max_tokens: 4096 }
  - id: siliconflow
    type: openai_compatible
    base_url: "https://api.siliconflow.cn/v1"
    api_key: ${SILICONFLOW_KEY}
    models:
      - name: deepseek-ai/DeepSeek-V2.5
      - name: Qwen/Qwen2-7B-Instruct
  - id: local_llamaguard
    type: openai_compatible
    base_url: "http://localhost:8080/v1"
    api_key: "dummy"
    models:
      - name: Meta-Llama-Guard-2-8B

models:
  flash: "deepseek_main/deepseek-chat"
  pro: "deepseek_main/deepseek-reasoner"
  cheap: "siliconflow/Qwen/Qwen2-7B-Instruct"
  safety: "local_llamaguard/Meta-Llama-Guard-2-8B"

tasks:
  pre_guard:
    model: "safety"
    fallback: "rule_based"
    timeout: 2
  intent_classify:
    model: "cheap"
  short_term_plan:
    model: "flash"
  main_response:
    model: "pro"
  simple_response:
    model: "flash"
  post_guard:
    model: "safety"

memory:
  short_term:
    provider: "redis_score"
    config:
      url: "redis://localhost:6379/0"
      ttl: 7200
      storage_limit: 30
      recall_limit: 6
      max_age_seconds: 1800
      scoring:
        importance_weights:
          has_order_number: 5
          has_product_name: 3
          requested_remember: 10
          is_resolved_marker: -5

knowledge:
  provider: "dify"
  config:
    api_base: "http://localhost:5001/v1"
    api_key: ${DIFY_API_KEY}
    retrieval_top_k: 3

routing:
  transfer:
    enabled: true
    default_target_url: "https://human-support.example.com/webhook"
    method: "POST"
    headers:
      Content-Type: "application/json"
    timeout: 5
    retry: 1
    auto_release_seconds: 600
    clear_memory_on_transfer: true
    freeze_memory_during_transfer: true

security:
  pre_guard:
    enabled: true
    rule_based_fallback: true
  post_guard:
    enabled: true

agent:
  system_prompt_template: |
    你是客服助手。使用知识库优先。禁止角色扮演。回复简洁礼貌。
    对话历史：{history}
    知识库：{context}
    用户：{user_input}
  response_templates:
    escalate: "已为您转接人工客服。"
    rejection: "请遵守对话规范。"
    interrupt_limit: "您输入太快，请稍后重试。"
  max_interrupt_count: 5
  escalate_keywords: ["人工客服", "转人工"]
  think_prompt: |
    根据对话输出JSON决策：{{"decision": "direct/rag/escalate", "reason": "..."}}
    对话：{history}
    输入：{user_input}

admin:
  api_key: ""
  log_file: "logs/app.log"

logging:
  file: "logs/app.log"
  level: "INFO"
```

---
