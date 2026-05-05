
# 智能客服后端 - The Implementation Plan (Decomposed and Prioritized Task List)

## [ ] Task 1: 项目初始化与配置管理器
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 创建项目目录结构
  - 实现 ConfigManager 单例，支持 YAML 加载与热重载
  - 支持环境变量替换 `${ENV_VAR}`
  - 实现文件监控与回调注册
- **Acceptance Criteria Addressed**: [AC-7]
- **Test Requirements**:
  - `programmatic` TR-1.1: ConfigManager 能正确加载 YAML 配置
  - `programmatic` TR-1.2: 环境变量能正确替换
  - `programmatic` TR-1.3: 文件修改能触发热重载回调
- **Notes**: 从配置模块开始，为后续功能提供基础

## [ ] Task 2: 供应商管理器与任务执行器
- **Priority**: P0
- **Depends On**: [Task 1]
- **Description**: 
  - 实现 Provider 抽象基类
  - 实现 OpenAICompatibleProvider
  - 实现 ProviderManager，管理多个供应商和模型别名
  - 实现 TaskExecutor，支持任务-模型绑定与降级
- **Acceptance Criteria Addressed**: [AC-1, AC-2]
- **Test Requirements**:
  - `programmatic` TR-2.1: ProviderManager 能正确返回模型实例
  - `programmatic` TR-2.2: TaskExecutor 能执行任务并处理降级
- **Notes**: 优先实现 OpenAI 兼容供应商

## [ ] Task 3: 短期记忆模块与会话管理
- **Priority**: P0
- **Depends On**: [Task 1]
- **Description**: 
  - 实现 Memory 抽象基类
  - 实现 RedisScoreMemory，支持基本存储与召回
  - 实现记忆冻结功能
  - 实现用户ID与会话映射管理（Redis）
  - 实现会话超时自动清理
- **Acceptance Criteria Addressed**: [AC-3, AC-9]
- **Test Requirements**:
  - `programmatic` TR-3.1: 能正确存储和加载会话消息
  - `programmatic` TR-3.2: 记忆冻结时不允许写入
  - `programmatic` TR-3.3: 同一用户ID能复用同一会话
  - `programmatic` TR-3.4: 会话超时时能自动清理
- **Notes**: 先实现基本功能，再添加凋落算法

## [ ] Task 3.5: 对话记录模块
- **Priority**: P0
- **Depends On**: [Task 1, Task 3]
- **Description**: 
  - 实现 ConversationHistory 抽象基类
  - 实现 RedisConversationHistory，完整记录会话历史
  - 与短期记忆模块分离，独立维护完整记录
  - 支持获取完整对话记录
- **Acceptance Criteria Addressed**: [AC-11]
- **Test Requirements**:
  - `programmatic` TR-3.5.1: 对话记录模块能完整记录会话历史
  - `programmatic` TR-3.5.2: 对话记录与短期记忆分离存储
  - `programmatic` TR-3.5.3: 能获取指定会话的完整对话记录

## [ ] Task 4: Agent 基础编排与主 API
- **Priority**: P0
- **Depends On**: [Task 2, Task 3, Task 3.5]
- **Description**: 
  - 使用 LangGraph 构建基础 Agent 图
  - 实现 listen、respond、update 等基础节点
  - 实现主 API `/v1/chat` 端点，接收 user_id 和 user_input
  - 在主 API 中集成用户ID与会话映射逻辑
  - 在 update 节点中同时更新短期记忆和对话记录
- **Acceptance Criteria Addressed**: [AC-3, AC-9, AC-11]
- **Test Requirements**:
  - `programmatic` TR-4.1: 基础对话流程能正常工作
  - `programmatic` TR-4.2: 主 API 能正确响应请求
  - `programmatic` TR-4.3: 主 API 接收 user_id 并维护会话
  - `programmatic` TR-4.4: 对话记录能与短期记忆同步更新

## [ ] Task 5: 安全审查模块
- **Priority**: P1
- **Depends On**: [Task 2]
- **Description**: 
  - 实现前置安全审查
  - 实现后置安全审查
  - 实现规则降级（正则过滤）
- **Acceptance Criteria Addressed**: [AC-5]
- **Test Requirements**:
  - `programmatic` TR-5.1: 前置审查能拦截违规输入
  - `programmatic` TR-5.2: 后置审查能替换违规输出
- **Notes**: 支持模型和规则两种方式

## [ ] Task 6: 知识库检索集成
- **Priority**: P1
- **Depends On**: [Task 1]
- **Description**: 
  - 实现 DifyRetriever
  - 实现 QdrantRetriever（可选降级）
- **Acceptance Criteria Addressed**: [AC-5]
- **Test Requirements**:
  - `programmatic` TR-6.1: 能正确从 Dify 检索知识库片段

## [ ] Task 7: 记忆凋落算法与重要性评分
- **Priority**: P1
- **Depends On**: [Task 3]
- **Description**: 
  - 实现重要性评分规则（正则匹配）
  - 实现记忆凋落算法（时间+重要性）
  - 集成到 add_messages 流程
- **Acceptance Criteria Addressed**: [AC-4]
- **Test Requirements**:
  - `programmatic` TR-7.1: 记忆超过存储限制时能正确凋落
  - `programmatic` TR-7.2: 重要性评分规则能正常工作

## [ ] Task 8: 会话转接与路由
- **Priority**: P1
- **Depends On**: [Task 3, Task 3.5, Task 4]
- **Description**: 
  - 实现会话状态管理（Redis）
  - 实现消息转发器
  - 实现 Agent 转接工具
  - 集成到主 API 路由逻辑
  - 转接时调用外部API需包含用户内容、用户ID和完整对话记录
  - 所有外部API调用输出内容包含输出内容和用户ID
- **Acceptance Criteria Addressed**: [AC-6, AC-10, AC-12]
- **Test Requirements**:
  - `programmatic` TR-8.1: 转接时能正确清空和冻结短期记忆
  - `programmatic` TR-8.2: 转接中的消息能正确转发
  - `programmatic` TR-8.3: 转接时发送的数据包含用户内容、用户ID和完整对话记录
  - `programmatic` TR-8.4: 所有外部API调用输出包含输出内容和用户ID

## [ ] Task 9: 管理 API
- **Priority**: P2
- **Depends On**: [Task 1, Task 2, Task 8]
- **Description**: 
  - 实现配置管理 API（GET/PUT）
  - 实现会话管理 API（release/transfer/clear）
  - 实现健康检查与日志 API
- **Acceptance Criteria Addressed**: [AC-8]
- **Test Requirements**:
  - `programmatic` TR-9.1: 配置 API 能正确读取和修改
  - `programmatic` TR-9.2: 会话管理 API 能正常工作

## [ ] Task 10: 完整集成与测试
- **Priority**: P2
- **Depends On**: [Task 1-9]
- **Description**: 
  - 端到端测试完整对话流程
  - 压力测试与性能优化
  - 文档编写
- **Acceptance Criteria Addressed**: [AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12]
- **Test Requirements**:
  - `programmatic` TR-10.1: 完整对话流程能正常工作
  - `programmatic` TR-10.2: 所有核心功能集成测试通过
