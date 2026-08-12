---
title: GitLab Webhook 与外部集成入门
date: 2026-08-28 13:00:00
tags:
  - GitLab
  - Webhook
  - 入门
categories:
  - GitLab 新手入门
---

**Webhook** 让 GitLab 事件通知外部系统（Slack、Jenkins、自建服务）。

## 配置 Webhook

**Settings → Webhooks**

| 字段 | 说明 |
|------|------|
| URL | 接收端 HTTPS 地址 |
| Secret token | 签名校验 |
| Trigger | Push、MR、Pipeline 等 |

## 常见 Trigger

| 事件 | 用途 |
|------|------|
| Push events | 触发外部 CI、同步镜像 |
| Merge request events | 通知 Review 机器人 |
| Pipeline events | 部署状态同步 |
| Job events | 单 Job 失败告警 |

## Payload 示例（Push）

```json
{
  "object_kind": "push",
  "ref": "refs/heads/main",
  "project": {
    "name": "my-api",
    "web_url": "https://gitlab.com/mygroup/my-api"
  },
  "commits": [...]
}
```

接收端验证 `X-Gitlab-Token` header。

## Slack 集成

**Settings → Integrations → Slack notifications**

或使用 Webhook 发到 Slack Incoming Webhook URL。

## 与 Jenkins 集成

Jenkins 安装 **GitLab Plugin**，Webhook URL：

```
https://jenkins.example.com/project/my-job
```

GitLab MR/Push 触发 Jenkins Pipeline。

## System Hook（管理员）

实例级所有项目事件，适合 **审计、SIEM**。

## 反模式

- Webhook URL 无 HTTPS
- 不验 Secret 可被伪造
- 同一事件重复配置多个相同 Webhook

Webhook 是 GitLab 融入 **现有工具链** 的桥梁。
