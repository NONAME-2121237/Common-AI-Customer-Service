
# 智能客服后端 - Product Requirement Document

## Overview
- **Summary**: 构建一个生产级智能客服后端系统，支持多供应商AI模型集成、会话管理、记忆凋落、安全审查、知识库检索和人工转接功能。
- **Purpose**: 提供低成本、高可控的智能客服解决方案，通过任务分级分配不同规模模型，支持人工介入和灵活的配置管理。
- **Target Users**: 企业客服团队、运营人员、技术维护人员

## Goals
- 实现多供应商AI模型兼容（OpenAI、Anthropic、Google Vertex等）
- 支持会话转接和人工介入，保护对话隐私
- 提供带重要性评分的短期记忆自动凋落
- 实现输入输出双重安全审查
- 配置驱动并支持热重载，无需重启即可生效
- 提供完整的管理API用于运维和监控

## Non-Goals (Out of Scope)
- 不实现前端界面（仅提供API）
- 不实现知识库文档管理UI（使用Dify）
- 不实现语音交互功能
- 不实现多语言支持（默认中文）

## Background & Context
- 项目基于Python构建，使用FastAPI作为Web框架
- 使用LangGraph进行Agent编排
- 使用Redis进行会话和记忆存储
- 使用Dify作为知识库管理系统

## Functional Requirements
- **FR-1**: 多供应商模型管理，支持OpenAI兼容、Anthropic、Google Vertex等
- **FR-2**: 任务分级与执行，不同任务使用不同规模模型
- **FR-3**: 短期记忆存储与自动凋落
- **FR-4**: 安全审查（前置+后置）
- **FR-5**: 知识库检索集成（Dify + Qdrant）
- **FR-6**: 会话状态管理与人工转接
- **FR-7**: 配置热重载
- **FR-8**: 管理API（配置、会话、日志、健康检查）

## Non-Functional Requirements
- **NFR-1**: 高可用性，支持模型降级和故障转移
- **NFR-2**: 响应及时，简单回复&lt;3s，复杂回复&lt;10s
- **NFR-3**: 可扩展性，支持水平扩展API节点
- **NFR-4**: 安全性，API密钥加密存储，管理接口仅本机访问

## Constraints
- **Technical**: Python 3.10+, FastAPI, LangGraph, Redis
- **Business**: 开发周期4周，核心功能优先
- **Dependencies**: Dify (知识库), Redis (缓存), 外部AI API

## Assumptions
- Redis服务可用并正常运行
- Dify服务已配置并可访问
- 外部AI API密钥已获取

## Acceptance Criteria

### AC-1: 模型供应商管理
- **Given**: 系统已启动并加载配置
- **When**: 用户通过ProviderManager请求模型
- **Then**: 系统能正确返回对应模型实例并调用成功
- **Verification**: `programmatic`
- **Notes**: 验证多种供应商类型（OpenAI兼容、Anthropic等）

### AC-2: 任务执行与降级
- **Given**: 系统已配置任务-模型绑定
- **When**: 执行任务时主模型失败
- **Then**: 系统能正确降级到备用模型或规则
- **Verification**: `programmatic`

### AC-3: 短期记忆存储与召回
- **Given**: 会话已创建并添加消息
- **When**: 加载会话记忆
- **Then**: 系统返回最近`recall_limit`条消息
- **Verification**: `programmatic`

### AC-4: 记忆凋落算法
- **Given**: 会话记忆超过`storage_limit`
- **When**: 添加新消息
- **Then**: 系统按分数规则自动淘汰低价值消息
- **Verification**: `programmatic`

### AC-5: 安全审查
- **Given**: 用户发送包含敏感内容的消息
- **When**: 前置/后置安全审查运行
- **Then**: 系统正确拒绝或替换违规内容
- **Verification**: `programmatic`

### AC-6: 人工转接
- **Given**: Agent调用转接工具或管理API手动转接
- **When**: 会话状态变为`transferred`
- **Then**: 系统清空记忆、冻结写入并转发消息到外部接口
- **Verification**: `programmatic`

### AC-7: 配置热重载
- **Given**: 配置文件已修改
- **When**: 文件变化被检测到
- **Then**: 系统自动重载配置，无需重启服务
- **Verification**: `programmatic`

### AC-8: 管理API功能
- **Given**: 管理API服务运行
- **When**: 调用管理接口（配置/会话/日志）
- **Then**: 接口正常响应并执行对应操作
- **Verification**: `programmatic`

## Open Questions
- [ ] 是否需要支持更多AI供应商？
- [ ] 是否需要实现消息推送通知？
- [ ] 是否需要实现多租户支持？
