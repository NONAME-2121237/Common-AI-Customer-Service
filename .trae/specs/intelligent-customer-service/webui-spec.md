
# 智能客服后端 WebUI - Product Requirement Document

## Overview
- **Summary**: 构建一个低代码但功能丰富的WebUI管理后台，支持多语言i18n（中英日），具备基于角色的权限管理能力。
- **Purpose**: 为客服团队提供可视化管理和监控界面，支持会话管理、人工服务、用户权限管理等功能。
- **Target Users**: 超级管理员、管理员、普通客服人员

## Goals
- 实现低代码、组件化的前端架构
- 支持i18n国际化（中英日），易于扩展新语言
- 实现基于角色的权限管理系统（RBAC）
- 提供会话监控和管理功能
- 支持人工接入服务
- 支持用户账号管理

## Non-Goals (Out of Scope)
- 不实现复杂的数据可视化图表
- 不实现移动端适配
- 不实现深度的个性化定制

## User Roles & Permissions

### 超级管理员 (Super Admin)
- 管理所有功能
- 分配权限给管理员
- 管理所有用户账号
- 修改后端配置
- 查看所有会话记录
- 人工服务所有会话

### 管理员 (Admin)
- 管理普通用户权限
- 创建/删除普通用户
- 查看所有会话
- 进行人工服务
- 修改部分后端配置（受限）

### 普通用户 (User)
- 查看当前会话列表
- 进行人工服务
- 回复会话（需权限）
- 仅浏览模式（仅查看，无操作权限）

## Functional Requirements
- **FR-1**: 用户认证系统（登录、登出、Session管理）
- **FR-2**: 基于角色的权限控制（RBAC）
- **FR-3**: 多语言支持（中文、英文、日文）
- **FR-4**: 会话列表与监控
- **FR-5**: 人工接入服务界面
- **FR-6**: 用户管理（CRUD）
- **FR-7**: 配置管理界面

## Non-Functional Requirements
- **NFR-1**: 响应及时，界面加载<2s
- **NFR-2**: 界面简洁易用
- **NFR-3**: 权限控制安全可靠

## Technology Stack
- React 18 + TypeScript
- Vite (构建工具)
- TailwindCSS (样式)
- React Router (路由)
- Zustand (状态管理)
- i18next (国际化)
- Axios (HTTP客户端)

## i18n Languages
- 中文 (zh-CN) - 默认
- English (en-US)
- 日本語 (ja-JP)

## Acceptance Criteria

### AC-1: 用户认证
- **Given**: 用户访问系统
- **When**: 输入正确的用户名密码
- **Then**: 成功登录并跳转到首页，显示对应角色的菜单
- **Verification**: programmatic

### AC-2: 权限控制
- **Given**: 用户已登录
- **When**: 访问超出权限的页面
- **Then**: 显示无权限提示或自动隐藏菜单项
- **Verification**: programmatic

### AC-3: 多语言切换
- **Given**: 用户已登录
- **When**: 切换语言设置
- **Then**: 界面所有文本立即更新为对应语言
- **Verification**: programmatic

### AC-4: 会话管理
- **Given**: 管理员/普通用户（有权限）登录
- **When**: 查看会话列表
- **Then**: 显示所有会话，支持筛选和搜索
- **Verification**: programmatic

### AC-5: 人工服务
- **Given**: 有权限用户登录
- **When**: 选择会话进行服务
- **Then**: 进入聊天界面，可以发送消息
- **Verification**: programmatic

### AC-6: 用户管理
- **Given**: 管理员/超级管理员登录
- **When**: 管理用户
- **Then**: 可以创建、编辑、删除用户，设置权限
- **Verification**: programmatic
