# 智能客服后端 - 产品需求文档

## Overview
- **Summary**: 生产级智能客服后端系统，具备多供应商多模型支持、完整会话生命周期管理、AI 记忆与聊天记录分离、转接人工能力、配置驱动热重载及完备的管理 API。
- **Purpose**: 提供企业级智能客服基础设施，支持灵活的模型调用策略、可靠的会话管理和便捷的运维能力。
- **Target Users**: 企业客服系统开发者、运维人员、客服管理人员。

## Goals
- 实现多供应商多模型支持，根据任务复杂度调用不同规模模型以控制成本
- 提供完整会话生命周期管理（创建、活动、转接、空闲超时关闭）
- 实现 AI 记忆与聊天记录分离，记忆采用凋落算法管理
- 支持清晰的转接人工流程（清空记忆、推送历史、实时转发）
- 实现完全配置驱动 + 热重载机制
- 提供完备的管理 API（配置、状态、日志、会话管理）

## Non-Goals (Out of Scope)
- 不提供前端界面，仅提供 API 接口
- 不实现知识库检索功能（可通过配置接入外部检索服务）
- 不负责人工客服系统本身的实现（仅提供转接接口）
- 不支持语音/多媒体消息处理

## Background & Context
- 当前企业智能客服需要灵活支持多种 AI 模型供应商
- 需要在成本控制和服务质量之间取得平衡
- 人工转接是客服系统的关键功能，需要保证数据完整性
- 运维人员需要实时监控和管理能力

## Functional Requirements
- **FR-1**: 主 API 提供 `POST /v1/chat` 端点，支持用户消息发送和 AI 回复接收
- **FR-2**: 会话管理支持创建、状态检查、空闲超时关闭、转接人工、记忆清空
- **FR-3**: 多供应商管理支持 OpenAI 兼容接口，支持模型别名映射
- **FR-4**: 任务执行器支持多个内置任务（pre_guard、intent_classify、short_term_plan、main_response、simple_response、post_guard）
- **FR-5**: Agent 编排支持状态图执行和输入打断
- **FR-6**: 短期记忆支持凋落算法，根据时间和重要性评分淘汰消息
- **FR-7**: 聊天记录独立存储，用于审计和人工转接
- **FR-8**: 转接人工流程支持清空记忆、推送历史记录、实时转发用户消息
- **FR-9**: 配置管理器支持 YAML 加载、环境变量占位符、热重载
- **FR-10**: 管理 API 提供配置查看/修改、健康检查、日志查看、会话管理等功能

## Non-Functional Requirements
- **NFR-1**: 配置修改热重载延迟 < 5 秒
- **NFR-2**: 会话创建和消息处理响应时间 < 500ms
- **NFR-3**: 支持 1000+ 并发会话
- **NFR-4**: 管理 API 仅监听 127.0.0.1，确保安全性
- **NFR-5**: 日志级别可动态调整

## Constraints
- **Technical**: Python 3.10+, FastAPI, Redis, LangGraph
- **Business**: 需支持主流 AI 供应商（DeepSeek、SiliconFlow 等）
- **Dependencies**: Redis 7.0+ 用于会话存储

## Assumptions
- 外部推送服务（push.endpoint）和转发服务（forward.url）已就绪
- Redis 服务已部署并可访问
- 环境变量（如 DEEPSEEK_KEY）已正确配置

## Acceptance Criteria

### AC-1: 正常对话流程
- **Given**: 用户调用 `POST /v1/chat` 携带有效 user_id 和 message
- **When**: 会话处于 active 状态且无安全问题
- **Then**: 系统生成 AI 回复，写入聊天记录和短期记忆，并异步推送至 push.endpoint
- **Verification**: `programmatic`

### AC-2: 会话空闲超时关闭
- **Given**: 会话超过 max_idle_seconds 无活动
- **When**: 用户发送新消息
- **Then**: 系统删除原有会话数据，创建新会话处理当前消息
- **Verification**: `programmatic`

### AC-3: 转接人工流程
- **Given**: Agent 决策 escalate 或调用 transfer_to_human 工具
- **When**: 转接流程执行
- **Then**: 清空短期记忆、推送历史记录至 forward.url、状态设为 transferred
- **Verification**: `programmatic`

### AC-4: 转接期间消息转发
- **Given**: 会话处于 transferred 状态
- **When**: 用户发送新消息
- **Then**: 消息直接转发至 forward.url，不经过 Agent，不写入记忆
- **Verification**: `programmatic`

### AC-5: 自动释放转接
- **Given**: 会话处于 transferred 状态超过 auto_release_seconds 无活动
- **When**: 用户发送新消息
- **Then**: 状态重置为 active，清除 memory_frozen
- **Verification**: `programmatic`

### AC-6: 短期记忆凋落算法
- **Given**: 写入新消息后总条数超过 storage_limit 或存在过期消息
- **When**: 触发凋落整理
- **Then**: 计算保留分数（时间因子×0.4 + 重要性×0.6），淘汰低分消息至容量上限
- **Verification**: `programmatic`

### AC-7: 配置热重载
- **Given**: 修改 config.yaml 文件
- **When**: 轮询检测到变化或手动触发重载
- **Then**: 配置自动更新，无需重启服务
- **Verification**: `programmatic`

### AC-8: 管理 API 认证
- **Given**: 配置了 admin.api_key
- **When**: 调用管理 API 未携带有效 Authorization 头
- **Then**: 返回 401 未授权错误
- **Verification**: `programmatic`

### AC-9: 敏感配置脱敏
- **Given**: 调用 GET /admin/config
- **When**: 响应返回配置信息
- **Then**: API key 等敏感字段被隐藏
- **Verification**: `human-judgment`

### AC-10: 供应商热重载重建
- **Given**: 修改 providers 配置并触发热重载
- **When**: 新请求到达
- **Then**: 使用新配置的供应商连接处理请求
- **Verification**: `programmatic`

## Open Questions
- [ ] 是否需要支持多租户模式？
- [ ] 是否需要提供消息队列支持异步处理？
- [ ] 是否需要支持消息加密传输？
