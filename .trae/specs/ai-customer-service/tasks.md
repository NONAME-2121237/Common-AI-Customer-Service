# 智能客服后端 - 实现计划

## [ ] Task 1: 项目初始化与基础配置
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 创建项目目录结构
  - 初始化 Python 虚拟环境
  - 安装核心依赖（FastAPI、Redis、LangGraph、PyYAML 等）
  - 创建基础配置文件 config.yaml
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-1.1: 项目结构正确创建，依赖安装成功
  - `programmatic` TR-1.2: config.yaml 可正确加载并解析环境变量占位符
- **Notes**: 使用 Poetry 或 pip 管理依赖，配置文件支持环境变量 `${VAR}` 格式

## [ ] Task 2: 配置管理器实现
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - 实现 ConfigManager 类，支持 YAML 加载和环境变量替换
  - 提供点号路径读取（如 `tasks.main_response.model`）
  - 支持配置写入并持久化（保留注释）
  - 实现文件监控（轮询）自动热重载
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-2.1: 点号路径读取返回正确值
  - `programmatic` TR-2.2: 配置修改后热重载生效（<5秒）
  - `programmatic` TR-2.3: 配置写入后 YAML 文件正确更新
- **Notes**: 使用 watchdog 或轮询方式检测文件变化

## [ ] Task 3: Redis 连接与会话存储抽象
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - 实现 Redis 连接池管理
  - 封装会话数据存储接口（用户映射、会话状态、短期记忆、聊天记录）
  - 定义 Redis 键约定和数据结构
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- **Test Requirements**:
  - `programmatic` TR-3.1: 用户映射正确存储和查询
  - `programmatic` TR-3.2: 会话状态正确读写
  - `programmatic` TR-3.3: 短期记忆 JSON 数组正确存储
- **Notes**: 使用 redis-py 库，支持 Redis 7.0+

## [ ] Task 4: 供应商管理器实现
- **Priority**: P0
- **Depends On**: Task 2
- **Description**: 
  - 实现 ProviderManager 类，管理多个供应商实例
  - 支持 OpenAI 兼容接口
  - 实现模型别名映射
  - 提供统一接口 `chat_completion(messages, model, **params)`
- **Acceptance Criteria Addressed**: AC-10
- **Test Requirements**:
  - `programmatic` TR-4.1: 供应商实例正确创建和管理
  - `programmatic` TR-4.2: 模型别名正确解析
  - `programmatic` TR-4.3: chat_completion 返回纯文本响应
- **Notes**: 使用 openai 库作为基础客户端

## [ ] Task 5: 任务执行器实现
- **Priority**: P0
- **Depends On**: Task 2, Task 4
- **Description**: 
  - 实现 TaskExecutor 类，支持内置任务（pre_guard、intent_classify、short_term_plan、main_response、simple_response、post_guard）
  - 根据任务名称获取模型，调用供应商
  - 支持超时与降级（回退到规则）
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-5.1: 各任务正确绑定模型
  - `programmatic` TR-5.2: 任务执行返回预期格式结果
  - `programmatic` TR-5.3: 超时和降级机制生效
- **Notes**: 使用 tenacity 实现重试逻辑

## [ ] Task 6: 短期记忆与凋落算法实现
- **Priority**: P0
- **Depends On**: Task 2, Task 3
- **Description**: 
  - 实现 ShortTermMemory 类
  - 实现凋落算法（时间因子×0.4 + 重要性×0.6）
  - 实现重要性评分（规则匹配或调用小模型）
  - 提供 get_history 方法返回最近 recall_limit 条
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-6.1: 写入消息后触发凋落整理
  - `programmatic` TR-6.2: 保留分数计算正确（时间因子+重要性）
  - `programmatic` TR-6.3: get_history 返回正确数量的消息
- **Notes**: 重要性评分规则可配置，支持订单号、关键词匹配

## [ ] Task 7: 聊天记录存储实现
- **Priority**: P0
- **Depends On**: Task 3
- **Description**: 
  - 实现 ChatLog 类，独立存储聊天记录
  - 支持消息追加和查询
  - 用于人工转接时提供完整历史
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-7.1: 消息正确追加到聊天记录
  - `programmatic` TR-7.2: 聊天记录查询返回正确顺序
  - `programmatic` TR-7.3: 聊天记录独立于短期记忆
- **Notes**: 使用 Redis List 存储，左进右出

## [ ] Task 8: 会话路由与转接实现
- **Priority**: P0
- **Depends On**: Task 2, Task 3, Task 6, Task 7
- **Description**: 
  - 实现 SessionRouter 类管理会话状态（active/transferred）
  - 实现转接流程（清空记忆、推送历史、状态转换）
  - 实现自动释放和手动释放逻辑
  - 实现空闲超时关闭逻辑
- **Acceptance Criteria Addressed**: AC-2, AC-3, AC-4, AC-5
- **Test Requirements**:
  - `programmatic` TR-8.1: 会话状态正确转换（active→transferred→active）
  - `programmatic` TR-8.2: 转接时清空短期记忆
  - `programmatic` TR-8.3: 空闲超时后会话正确关闭
  - `programmatic` TR-8.4: 转接期间消息直接转发
- **Notes**: 使用 Redis Hash 存储会话状态

## [ ] Task 9: 推送与转发实现
- **Priority**: P0
- **Depends On**: Task 2, Task 8
- **Description**: 
  - 实现 PushService 类，异步推送回复至 push.endpoint
  - 实现 ForwardService 类，转发消息至 forward.url
  - 统一消息格式（session_id, user_id, sender, content, timestamp）
- **Acceptance Criteria Addressed**: AC-1, AC-3, AC-4
- **Test Requirements**:
  - `programmatic` TR-9.1: 推送消息格式正确
  - `programmatic` TR-9.2: 转发消息格式正确
  - `programmatic` TR-9.3: 异步推送不阻塞主流程
- **Notes**: 使用 httpx 进行 HTTP 请求，支持重试

## [ ] Task 10: Agent 编排（LangGraph）实现
- **Priority**: P0
- **Depends On**: Task 2, Task 5
- **Description**: 
  - 使用 LangGraph 构建状态图
  - 节点：listen → classify → think → decide → act → respond → post_check → update → check_interrupt
  - 支持输入打断机制
  - 提示词模板从配置读取
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-10.1: 状态图正确执行各节点
  - `programmatic` TR-10.2: 输入打断机制生效
  - `programmatic` TR-10.3: 提示词模板从配置正确加载
- **Notes**: 使用 LangGraph 的 interrupt 功能支持打断

## [ ] Task 11: 主 API 实现（端口 8000）
- **Priority**: P0
- **Depends On**: Task 3, Task 8, Task 9, Task 10
- **Description**: 
  - 实现 `POST /v1/chat` 端点
  - 处理会话映射、状态检查、调用 Agent 编排
  - 同步返回回复，异步推送
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3, AC-4, AC-5
- **Test Requirements**:
  - `programmatic` TR-11.1: POST /v1/chat 返回正确格式响应
  - `programmatic` TR-11.2: 新用户创建新会话
  - `programmatic` TR-11.3: 转接状态消息直接转发
- **Notes**: 使用 FastAPI 构建 REST API

## [ ] Task 12: 管理 API 实现（端口 8001）
- **Priority**: P1
- **Depends On**: Task 2, Task 3, Task 4, Task 8
- **Description**: 
  - 实现管理 API 端点（配置、供应商、模型、任务、会话、日志）
  - 实现认证机制（Bearer Token）
  - 实现会话管理操作（释放、转接、清空、删除）
- **Acceptance Criteria Addressed**: AC-8, AC-9
- **Test Requirements**:
  - `programmatic` TR-12.1: 认证机制生效（未授权返回 401）
  - `programmatic` TR-12.2: 敏感配置字段脱敏
  - `programmatic` TR-12.3: 会话管理操作正确执行
- **Notes**: 管理 API 仅监听 127.0.0.1

## [ ] Task 13: 主程序入口与服务启动
- **Priority**: P0
- **Depends On**: Task 11, Task 12
- **Description**: 
  - 创建主程序入口文件 main.py
  - 启动主 API 和管理 API 服务
  - 初始化所有组件
- **Acceptance Criteria Addressed**: AC-1, AC-8
- **Test Requirements**:
  - `programmatic` TR-13.1: 服务启动成功，端口 8000 和 8001 监听正常
  - `programmatic` TR-13.2: 所有组件初始化完成
- **Notes**: 使用 uvicorn 作为 ASGI 服务器

## [ ] Task 14: 单元测试与集成测试
- **Priority**: P1
- **Depends On**: 所有任务
- **Description**: 
  - 编写单元测试覆盖核心模块
  - 编写集成测试覆盖主要流程
  - 使用 pytest 运行测试
- **Acceptance Criteria Addressed**: 所有 AC
- **Test Requirements**:
  - `programmatic` TR-14.1: 单元测试覆盖率 > 80%
  - `programmatic` TR-14.2: 集成测试覆盖正常对话、转接、超时流程
- **Notes**: 使用 pytest-asyncio 支持异步测试

## [ ] Task 15: 日志与监控配置
- **Priority**: P2
- **Depends On**: Task 13
- **Description**: 
  - 配置结构化日志输出
  - 支持日志级别动态调整
  - 配置日志文件轮转
- **Acceptance Criteria Addressed**: NFR-5
- **Test Requirements**:
  - `programmatic` TR-15.1: 日志级别动态调整生效
  - `human-judgment` TR-15.2: 日志格式清晰，包含必要上下文
- **Notes**: 使用 structlog 进行结构化日志
