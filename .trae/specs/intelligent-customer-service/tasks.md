
# 智能客服后端 - The Implementation Plan (Decomposed and Prioritized Task List)

## [ ] Task 1: 项目初始化与配置管理器
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 创建项目目录结构
  - 实现ConfigManager单例，支持YAML加载与热重载
  - 支持环境变量替换${ENV_VAR}
  - 实现文件监控与回调注册
- **Acceptance Criteria Addressed**: [AC-7]
- **Test Requirements**:
  - programmatic TR-1.1: ConfigManager能正确加载YAML配置
  - programmatic TR-1.2: 环境变量能正确替换
  - programmatic TR-1.3: 文件修改能触发热重载回调
- **Notes**: 从配置模块开始，为后续功能提供基础

## [ ] Task 2: 供应商管理器与任务执行器
- **Priority**: P0
- **Depends On**: [Task 1]
- **Description**: 
  - 实现Provider抽象基类
  - 实现OpenAICompatibleProvider
  - 实现ProviderManager，管理多个供应商和模型别名
  - 实现TaskExecutor，支持任务-模型绑定与降级
  - 外部API调用输出包含输出内容和user_id
- **Acceptance Criteria Addressed**: [AC-1, AC-2, AC-11]
- **Test Requirements**:
  - programmatic TR-2.1: ProviderManager能正确返回模型实例
  - programmatic TR-2.2: TaskExecutor能执行任务并处理降级
  - programmatic TR-2.3: 外部API调用输出包含user_id
- **Notes**: 优先实现OpenAI兼容供应商

## [ ] Task 3: 短期记忆与用户会话管理
- **Priority**: P0
- **Depends On**: [Task 1]
- **Description**: 
  - 实现Memory抽象基类
  - 实现RedisScoreMemory（基本FIFO）
  - 实现记忆冻结功能
  - 实现用户ID与会话映射管理（Redis）
  - 实现会话超时自动清理
- **Acceptance Criteria Addressed**: [AC-3, AC-9]
- **Test Requirements**:
  - programmatic TR-3.1: 能正确存储和加载会话消息
  - programmatic TR-3.2: 记忆冻结时不允许写入
  - programmatic TR-3.3: 同一user_id能复用同一会话
  - programmatic TR-3.4: 会话超时时能自动清理
- **Notes**: 先实现基本功能，后续添加凋落算法

## [ ] Task 4: 对话记录模块
- **Priority**: P0
- **Depends On**: [Task 1, Task 3]
- **Description**: 
  - 实现ConversationHistory抽象基类
  - 实现RedisConversationHistory，完整记录会话历史
  - 与短期记忆模块分离，独立维护完整记录
  - 支持获取完整对话记录
- **Acceptance Criteria Addressed**: [AC-10]
- **Test Requirements**:
  - programmatic TR-4.1: 对话记录模块能完整记录会话历史
  - programmatic TR-4.2: 对话记录与短期记忆分离存储
  - programmatic TR-4.3: 能获取指定会话的完整对话记录
- **Notes**: 对话记录不做凋落，完整保存

## [ ] Task 5: Agent基础编排与主API
- **Priority**: P0
- **Depends On**: [Task 2, Task 3, Task 4]
- **Description**: 
  - 使用LangGraph构建基础Agent图
  - 实现listen、respond、update等基础节点
  - 实现主API /v1/chat端点，接收user_id和user_input
  - 在主API中集成用户ID与会话映射逻辑
  - 在update节点中同时更新短期记忆和对话记录
- **Acceptance Criteria Addressed**: [AC-3, AC-9, AC-10]
- **Test Requirements**:
  - programmatic TR-5.1: 基础对话流程能正常工作
  - programmatic TR-5.2: 主API能正确响应请求
  - programmatic TR-5.3: 主API接收user_id并维护会话
  - programmatic TR-5.4: 对话记录能与短期记忆同步更新

## [ ] Task 6: 安全审查模块
- **Priority**: P1
- **Depends On**: [Task 2]
- **Description**: 
  - 实现前置安全审查
  - 实现后置安全审查
  - 实现规则降级（正则过滤）
- **Acceptance Criteria Addressed**: [AC-5]
- **Test Requirements**:
  - programmatic TR-6.1: 前置审查能拦截违规输入
  - programmatic TR-6.2: 后置审查能替换违规输出
- **Notes**: 支持模型和规则两种方式

## [ ] Task 7: 知识库检索集成
- **Priority**: P1
- **Depends On**: [Task 1]
- **Description**: 
  - 实现DifyRetriever
  - 实现QdrantRetriever（可选降级）
- **Acceptance Criteria Addressed**: [AC-5]
- **Test Requirements**:
  - programmatic TR-7.1: 能正确从Dify检索知识库片段

## [ ] Task 8: 记忆凋落算法与重要性评分
- **Priority**: P1
- **Depends On**: [Task 3]
- **Description**: 
  - 实现重要性评分规则（正则匹配）
  - 实现记忆凋落算法（时间+重要性）
  - 集成到add_messages流程
- **Acceptance Criteria Addressed**: [AC-4]
- **Test Requirements**:
  - programmatic TR-8.1: 记忆超过存储限制时能正确凋落
  - programmatic TR-8.2: 重要性评分规则能正常工作
- **Notes**: 对话记录不受凋落影响

## [ ] Task 9: 会话转接与路由
- **Priority**: P1
- **Depends On**: [Task 3, Task 4, Task 5]
- **Description**: 
  - 实现会话状态管理（Redis）
  - 实现消息转发器，转发时包含user_id
  - 实现Agent转接工具
  - 集成到主API路由逻辑
  - 转接时调用外部API需包含用户内容、用户ID和完整对话记录
  - 所有外部API调用输出内容包含输出内容和用户ID
- **Acceptance Criteria Addressed**: [AC-6, AC-11, AC-12]
- **Test Requirements**:
  - programmatic TR-9.1: 转接时能正确清空和冻结短期记忆
  - programmatic TR-9.2: 转接中的消息能正确转发
  - programmatic TR-9.3: 转接时发送的数据包含用户内容、用户ID和完整对话记录
  - programmatic TR-9.4: 所有外部API调用输出包含输出内容和用户ID

## [ ] Task 10: 管理API
- **Priority**: P2
- **Depends On**: [Task 1, Task 2, Task 9]
- **Description**: 
  - 实现配置管理API（GET/PUT）
  - 实现会话管理API（release/transfer/clear）
  - 实现健康检查与日志API
- **Acceptance Criteria Addressed**: [AC-8]
- **Test Requirements**:
  - programmatic TR-10.1: 配置API能正确读取和修改
  - programmatic TR-10.2: 会话管理API能正常工作

## [ ] Task 11: 完整集成与测试
- **Priority**: P2
- **Depends On**: [Task 1-10]
- **Description**: 
  - 端到端测试完整对话流程
  - 压力测试与性能优化
  - 文档编写
- **Acceptance Criteria Addressed**: [AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12]
- **Test Requirements**:
  - programmatic TR-11.1: 完整对话流程能正常工作
  - programmatic TR-11.2: 所有核心功能集成测试通过
