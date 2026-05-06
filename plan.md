## 一、总体定位

生产级智能客服后端，具备：

- **多供应商、多模型、任务分级**：根据任务复杂度调用不同规模模型，控制成本。
- **完整会话生命周期管理**：自动创建、空闲超时关闭、转接人工、记忆清空。
- **AI 记忆与聊天记录分离**：AI 记忆用于上下文推理（凋落算法），聊天记录用于审计与人工转接。
- **转接人工行为清晰**：清空 AI 记忆、推送历史记录、实时转发用户消息。
- **完全配置驱动 + 热重载**：所有可变参数通过 YAML 管理，运行时修改无需重启。
- **管理 API**：本机回环端口，供呈现模块运维（配置、状态、日志、会话列表/内容、强制操作）。

---

## 二、核心模块与职责

### 1. 主 API（对外，端口 8000）
- 端点：`POST /v1/chat`
- 请求：`{"user_id": "xxx", "message": "..."}`
- 响应：同步返回 `{"user_id": "xxx", "reply": "..."}`，同时异步推送回复至配置的 `push.endpoint`。
- 职责：会话映射、状态检查、调用 Agent 编排、触发转接流程、管理空闲超时。

### 2. 管理 API（对内，端口 8001，监听 127.0.0.1）
- 提供配置查看/修改、组件健康检查、日志查看、会话列表/聊天内容查询、会话强制释放/转接/删除等操作。
- 供本地呈现模块调用。

### 3. 配置管理器
- 加载 `config.yaml`，支持环境变量占位符（`${VAR}`）。
- 提供点号路径读取（如 `tasks.main_response.model`）。
- 支持写入配置并持久化（保留注释），自动触发热重载。
- 文件监控（轮询）自动重载，也可手动调用。

### 4. 供应商管理器
- 管理多个供应商实例，每个实例由 `(base_url, api_key, type)` 唯一标识。
- 每个实例挂载多个模型（如 `flash`、`pro`），模型 ID 格式 `{provider_id}/{model_name}`。
- 支持全局模型别名（如 `flash` → `deepseek_main/deepseek-chat`）。
- 统一接口 `chat_completion(messages, model, **params)` 返回纯文本。
- 热重载时重建全部 Provider 实例（关闭旧连接，创建新连接）。

### 5. 任务执行器
- 内置任务：`pre_guard`, `intent_classify`, `short_term_plan`, `main_response`, `simple_response`, `post_guard`。
- 每个任务通过配置绑定一个模型 ID。
- 执行器根据任务名称获取模型，调用供应商，合并参数，返回结果。支持超时与降级（如回退到规则）。

### 6. Agent 编排（LangGraph）
- 状态图节点：`listen` → `classify` → `think` → `decide` → `act` → `respond` → `post_check` → `update` → `check_interrupt`。
- 支持输入打断：同一会话新消息可中断当前生成，最多可配置打断次数。
- 所有提示词模板（系统提示、思考提示）从配置读取，热重载生效。

### 7. 短期记忆（AI 记忆）
- 独立存储，每个会话一个 Redis JSON 数组，每条消息含 `role`, `content`, `timestamp`, `importance_score`, `metadata`。
- 凋落算法：每次写入后，若总条数 > `storage_limit` 或存在消息年龄 > `max_age_seconds`，计算保留分数（时间因子×0.4 + 重要性归一化分数×0.6），淘汰低分消息至容量上限。
- 重要性评分：规则匹配（订单号、关键词“请记住”等）或调用小模型，分值 0~10。
- `get_history` 返回最近 `recall_limit` 条。

### 8. 聊天记录（审计日志）
- 独立存储（Redis List 或数据库），保存用户和机器人的所有消息，字段同转发格式（`sender`, `content`, `timestamp`）。
- 用于人工转接时提供完整历史，以及问题追溯。
- 不参与 AI 推理。

### 9. 会话路由与转接
- 每个会话状态：`active` 或 `transferred`。
- Agent 可调用 `transfer_to_human` 工具触发转接。
- 转接时：清空短期记忆，设置 `memory_frozen=true`，获取聊天记录，逐条发送到 `forward.url`，状态置为 `transferred`，记录 `transferred_at`、`auto_release_at`。
- 转接期间：用户消息直接转发到 `forward.url`（不经过 Agent），不写入记忆，更新 `last_active`。
- 自动释放（转接状态）：超过 `auto_release_seconds` 无活动，状态重置为 `active`，清除 `memory_frozen`（聊天记录保留）。
- 会话空闲超时（全局）：无论何种状态，超过 `max_idle_seconds` 无活动，彻底关闭会话（删除短期记忆、聊天记录、路由状态、用户映射）。

### 10. 推送与转发
- 后端生成回复后，调用配置的 `push.endpoint` 将回复异步推送给前端。
- 转接时历史记录和实时用户消息，调用 `forward.url` 发送（统一格式）。

---

## 三、关键流程细则

### 1. 正常对话流程

1. 前端 `POST /v1/chat` 携带 `user_id` 和 `message`。
2. 后端根据 `user_id` 查找 `session_id`：
   - 若不存在或会话因空闲超时已关闭，则创建新会话（生成新 `session_id`，初始化空聊天记录、空短期记忆、状态 `active`、`created_at`、`last_active`）。
3. 更新 `last_active` 为当前时间。
4. 检查会话状态：
   - 若为 `transferred`：跳过 Agent，直接调用 `forward.url` 转发用户消息（`sender=user`），返回 200（无回复），流程结束。
   - 若为 `active`：继续。
5. 加载短期记忆（最近 `recall_limit` 条）到 Agent 状态。
6. 前置安全审查（调用 `pre_guard` 任务）：
   - 若检出注入/越狱 → 返回拒绝话术，保存到聊天记录，异步推送，流程结束。
7. 意图分类（可选，调用 `intent_classify` 任务）。
8. 短期规划（调用 `short_term_plan` 任务）→ 输出决策 `direct` / `rag` / `escalate`。
9. 若决策 `rag` → 调用知识库检索，获得相关片段。
10. 生成回复：
    - 若决策 `escalate` → 执行转接流程（见下）。
    - 否则调用 `main_response` 或 `simple_response` 任务生成回复。
11. 后置安全审查（调用 `post_guard` 任务）：
    - 若检出违规 → 替换为转接话术或拒绝话术。
12. 将本轮对话（用户消息 + AI 回复）写入聊天记录。
13. 将本轮对话写入短期记忆（若 `memory_frozen=false`），触发凋落整理。
14. 异步调用 `push.endpoint` 发送回复内容。
15. 同步返回 `{"user_id": "xxx", "reply": "..."}`。

### 2. 转接人工流程

**触发**：Agent 决策 `escalate` 或调用 `transfer_to_human` 工具。

**步骤**：

1. 清空短期记忆（删除 `memory:session:{session_id}`）。
2. 设置 `memory_frozen=true`。
3. 从聊天记录中获取该会话所有消息（按时间正序）。
4. 对于每条消息，调用 `forward.url` 发送（格式：`session_id`, `user_id`, `sender`, `content`, `timestamp`）。
5. 将会话路由状态设为 `transferred`，记录 `transferred_at`、`auto_release_at = now + auto_release_seconds`、`last_active`。
6. 返回同步响应 `{"reply": "您的问题已转接人工客服，请稍候。"}`，并异步推送该消息。

**转接期间**：

- 用户新消息 → 直接调用 `forward.url` 发送（`sender=user`），更新 `last_active`，不返回 AI 回复。
- 外部人工系统应通过自己的渠道回复用户（后端不负责人工回复）。

**释放转接**（回到机器人）：

- 自动释放：每次用户消息到达时检查 `now - last_active > auto_release_seconds` 且状态为 `transferred`，则将状态设为 `active`，清除 `memory_frozen`（聊天记录保留，短期记忆已空）。
- 手动释放：外部系统调用管理 API `POST /admin/session/release`，同样重置状态。

**会话彻底关闭**（空闲超时）：

- 每次用户消息到达时检查 `now - last_active > max_idle_seconds`，若超过则执行：
  - 删除短期记忆
  - 删除聊天记录
  - 删除路由状态
  - 删除 `user_id → session_id` 映射
  - 然后创建新会话处理当前消息（视为新会话）。

### 3. 统一消息转发格式（`forward.url` 和 `push.endpoint` 共用同一格式）

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | 后端会话标识 |
| `user_id` | string | 用户标识 |
| `sender` | string | `"user"` 或 `"agent"` |
| `content` | string | 消息内容 |
| `timestamp` | int | Unix 秒级时间戳 |

**注意**：`push.endpoint` 只发送 AI 生成的回复（`sender=agent`），而 `forward.url` 在转接时会发送历史记录和实时用户消息（`sender` 可 `user` 或 `agent`）。

### 4. 会话数据存储（Redis 键约定）

| 用途 | 键格式 | 数据结构 |
|------|--------|----------|
| 用户映射 | `user:session:{user_id}` | string（存储 session_id） |
| 会话路由状态 | `session:{session_id}:state` | hash 或 JSON（status, last_active, created_at, transferred_at, auto_release_at, memory_frozen） |
| AI 短期记忆 | `memory:session:{session_id}` | JSON 数组 |
| 聊天记录 | `chatlog:session:{session_id}` | list（左进右出，每条为 JSON 含 sender, content, timestamp） |

---

## 四、配置体系（`config.yaml` 核心段）

```yaml
app:
  name: "智能客服后端"
  max_agent_iterations: 5

providers:
  - id: deepseek_main
    type: openai_compatible
    base_url: "https://api.deepseek.com/v1"
    api_key: ${DEEPSEEK_KEY}
    models:
      - name: deepseek-chat
      - name: deepseek-reasoner
  # 可增加其他供应商，如 siliconflow, local_llamaguard 等

models:
  flash: "deepseek_main/deepseek-chat"
  pro: "deepseek_main/deepseek-reasoner"
  safety: "local_llamaguard/Meta-Llama-Guard-2-8B"   # 假设已配置

tasks:
  pre_guard:    { model: "safety", fallback: rule_based }
  intent_classify: { model: "flash" }
  short_term_plan: { model: "flash" }
  main_response: { model: "pro" }
  simple_response: { model: "flash" }
  post_guard:   { model: "safety" }

memory:
  short_term:
    storage_limit: 30
    recall_limit: 6
    max_age_seconds: 1800
    scoring:
      importance_weights:
        has_order_number: 5
        requested_remember: 10

session:
  max_idle_seconds: 1800          # 全局会话空闲超时（彻底关闭）

routing:
  transfer:
    enabled: true
    auto_release_seconds: 600     # 转接后无活动自动回到 active
    clear_memory_on_transfer: true
    freeze_memory_during_transfer: true

forward:
  url: "https://your-system/messages"
  method: "POST"
  headers:
    Content-Type: "application/json"
    Authorization: "Bearer ${FORWARD_TOKEN}"
  timeout: 5
  retry: 2

push:
  endpoint: "https://your-push-service/send"
  headers:
    Content-Type: "application/json"
  timeout: 5

admin:
  api_key: ""                     # 留空则无认证（本机）
  log_file: "logs/app.log"

logging:
  level: "INFO"
```

**热重载支持**：
- 修改 `providers` 或 `forward.url` 等网络配置时自动重建连接。
- 其他参数（任务映射、记忆参数、超时阈值）修改后立即生效，无需重启。

---

## 五、管理 API 完整端点清单

所有管理 API 监听 `127.0.0.1:8001`，路径前缀 `/admin`。认证方式：若配置了 `admin.api_key`，则请求需携带 `Authorization: Bearer <key>`。

| 方法 | 端点 | 功能 | 请求示例/说明 |
|------|------|------|----------------|
| GET | `/admin/config` | 获取脱敏配置 | 返回完整配置，隐藏敏感字段 |
| PUT | `/admin/config` | 更新扁平配置项 | Body: `{"path": "tasks.main_response.model", "value": "new_model"}` |
| GET | `/admin/config/raw` | 获取原始 YAML | 返回 `{"raw_yaml": "..."}` |
| PUT | `/admin/config/raw` | 整体替换 YAML | Body: `{"raw_yaml": "..."}`，持久化并热重载 |
| GET | `/admin/providers` | 列出供应商及模型 | 返回每个供应商的 id, type, base_url(脱敏), models |
| GET | `/admin/models` | 列出所有模型 ID 及别名 | 包含 `model_id` -> `provider_id/model_name` 以及别名映射 |
| GET | `/admin/tasks` | 查看任务-模型绑定 | 每个任务的 `name` 和绑定的 `model_id` |
| POST | `/admin/tasks/{task_name}/model` | 修改任务模型 | Body: `{"model_id": "new_model"}`，热重载 |
| GET | `/admin/components/status` | 健康检查 | 返回各组件（供应商、Redis、Dify 等）状态 |
| POST | `/admin/reboot/component` | 重启组件 | Body: `{"component": "provider_manager"}` |
| GET | `/admin/sessions` | 获取会话列表 | 支持参数 `status`, `user_id`, `limit`, `offset`, `order_by`, `order` |
| GET | `/admin/sessions/{session_id}/messages` | 获取会话聊天记录 | 支持参数 `limit`, `offset`；返回完整消息列表 |
| GET | `/admin/sessions/transferred` | 快捷获取转接中会话 | 相当于 `/admin/sessions?status=transferred` |
| POST | `/admin/session/release` | 释放转接回到 active | Body: `{"session_id": "xxx"}`，不清聊天记录 |
| POST | `/admin/session/transfer` | 强制转接（清空记忆并推送历史） | Body: `{"session_id": "xxx", "reason": "manual"}` |
| POST | `/admin/session/clear` | 清空 AI 短期记忆 | Body: `{"session_id": "xxx"}` |
| POST | `/admin/session/delete` | 彻底删除会话（所有数据） | Body: `{"session_id": "xxx"}` |
| GET | `/admin/logs` | 获取最近日志 | 参数 `lines`（默认 100） |
| POST | `/admin/logs/level` | 调整日志级别 | Body: `{"level": "DEBUG"}` |

**会话列表响应示例**：
```json
{
  "total": 42,
  "limit": 20,
  "offset": 0,
  "sessions": [
    {
      "session_id": "sess_abc",
      "user_id": "user_123",
      "status": "active",
      "created_at": 1712345678,
      "last_active": 1712346000,
      "memory_frozen": false,
      "message_count": 12
    }
  ]
}
```

**聊天内容响应示例**：
```json
{
  "session_id": "sess_abc",
  "user_id": "user_123",
  "total": 42,
  "limit": 20,
  "offset": 0,
  "messages": [
    {"sender": "user", "content": "我要退货", "timestamp": 1712345678},
    {"sender": "agent", "content": "请提供订单号", "timestamp": 1712345685}
  ]
}
```

---

## 六、设计总结

- **完整会话生命周期**：创建、活动、转接、空闲超时关闭，全程可观测。
- **记忆与记录分离**：AI 记忆带凋落，聊天记录独立存储，互不干扰。
- **转接人工**：行为明确，清空记忆、推送历史、实时转发，结束时可保留或删除记录。
- **配置驱动 + 热重载**：几乎所有参数可运行时调整。
- **管理 API 完备**：提供配置、状态、日志、会话列表/内容、强制操作等一切运维所需。
