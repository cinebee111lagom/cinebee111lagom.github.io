---
title: 阿里云账号治理：RAM、资源组与 Tag
date: 2026-08-25 09:30:00
tags:
  - 阿里云
  - RAM
  - 治理
categories:
  - 阿里云资源 SRE
---

云资源治理是 SRE 基础，**RAM + 资源组 + Tag** 实现权限、隔离与成本归因。

## 多账号模型（推荐）

```
管理账号（Organizations）
├── 生产账号 prod
├── 预发账号 staging
├── 测试账号 dev
└── 安全/日志账号 audit
```

资源隔离、账单分离、 blast radius 可控。

## RAM 角色与策略

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

| 原则 | 说明 |
|------|------|
| 最小权限 | 按角色分配，禁止 *:* |
| 使用角色 | ECS/ACK 用 RAM Role，非 AK |
| 禁止主账号 AK | 日常操作用 RAM 用户 |
| MFA | 管理员强制 MFA |

## 资源组

```
资源组：prod-web
  ├── ECS、SLB、RDS 归属
  └── 按项目/环境隔离视图
```

## Tag 规范（强制）

| Tag Key | 示例 | 用途 |
|---------|------|------|
| env | prod / staging | 环境 |
| project | payment | 项目 |
| owner | team-platform | 负责人 |
| cost-center | cc-001 | 成本中心 |

```bash
# CLI 按 Tag 查资源
aliyun ecs DescribeInstances --RegionId cn-hangzhou \
  --Tag.1.Key env --Tag.1.Value prod
```

## 操作审计

- **ActionTrail**：API 调用审计，投递 SLS
- 敏感操作告警（Delete、ModifySecurityGroup）

## Checklist

- [ ] 主账号无日常 AK
- [ ] 生产/测试账号分离
- [ ] Tag 策略强制（RAM 拒绝无 Tag 创建）
- [ ] ActionTrail 全 Region 开启
- [ ] 季度权限 review

账号治理是**云上安全与成本的第一道闸**。
