---
title: 阿里云 RAM 权限与安全基线
date: 2026-08-26 11:45:00
tags:
  - 阿里云
  - RAM
  - 安全
categories:
  - 阿里云资源 SRE
---

RAM 是阿里云访问控制核心，SRE 需落实最小权限与审计。

## 原则

```
禁止主账号日常操作
每人独立 RAM 用户 / SSO
AK 仅给程序，定期轮换
最小权限 Policy
```

## 用户与角色

| 类型 | 用途 |
|------|------|
| RAM 用户 | 人员登录控制台/CLI |
| RAM 角色 | ECS/ACK 实例、跨账号 |
| STS | 临时凭证 |

```bash
# CLI 使用 RAM 用户
aliyun configure --profile prod
```

## 权限策略示例

```json
{
  "Version": "1",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ecs:Describe*",
      "rds:Describe*"
    ],
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "acs:ResourceTag/env": "prod"
      }
    }
  }]
}
```

## 权限边界

```
PowerUser 禁止 IAM 类操作
开发：只读 + 特定资源组
SRE：运维 Action 白名单
```

## 安全基线

| 项 | 要求 |
|----|------|
| MFA | 全员强制 |
| 密码策略 | 复杂度 + 90 天轮换 |
| AK | 不用则删，180 天轮换 |
| 操作审计 | ActionTrail 全 Region |
| 配置审计 | 云安全中心 / Config 规则 |

## ActionTrail

```
所有 API 调用 → OSS/SLS
异常：DeleteDBInstance、DeleteBucket
```

## 检查清单

- [ ] 无主账号 AK
- [ ] MFA 100%
- [ ] ActionTrail 开启
- [ ] 高危 API 告警
- [ ] 季度权限 review

RAM 误配 = **删库/run 权限**，变更需双人复核。
