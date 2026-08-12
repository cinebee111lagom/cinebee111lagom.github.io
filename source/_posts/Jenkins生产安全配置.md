---
title: Jenkins 生产安全配置
date: 2026-08-23 11:30:00
tags:
  - Jenkins
  - 安全
categories:
  - Jenkins SRE
---

Jenkins 历史上是攻击面较大的系统，生产必须 hardened。

## 认证与授权

| 项 | 生产配置 |
|----|----------|
| 安全realm | LDAP/OAuth/SAML，禁用本地弱密码 |
| 授权策略 | Role-Based Strategy |
| 匿名 | 无权限 |
| Overall/Administer | 最小人数 |

```groovy
// Role-Based 示例
// admin → Overall/Administer
// developer → Job/Build/Read on folder-dev/*
// viewer → Overall/Read
```

## CSRF

```
启用 Default Crumb Issuer
API 调用带 Jenkins-Crumb header
```

## Agent 安全

```
Agent → Controller 仅内网 50000
启用 Agent → Master Access Control（白名单命令）
禁止 Agent 以 root 运行（K8s securityContext）
```

## Script Approval

- Pipeline 中 `@NonCPS`、`Method` 需管理员批准
- 定期 **In-process Script Approval** 审计

## 插件安全

- 最小插件原则
- 禁用未使用插件
- 关注 [Jenkins Security Advisories](https://www.jenkins.io/security/)
- staging 先升级

## 网络

```
Jenkins UI → HTTPS + 内网/VPN
Webhook → 专用 ingress + IP 白名单（GitHub/GitLab）
Script Console → 仅 admin，考虑禁用
```

## 凭据

- 不入 Jenkinsfile 明文
- 用 credentials binding
- 定期轮换 + Audit Trail 插件

## Audit Trail

记录配置变更、登录、Job 修改。

## Checklist

- [ ] HTTPS 强制
- [ ] RBAC 按 Folder 隔离
- [ ] CSRF 开启
- [ ] Script Console 受限
- [ ] 插件 CVE 订阅
- [ ] Agent 非 root

Jenkins 安全是**持续补丁 + 最小权限**。
