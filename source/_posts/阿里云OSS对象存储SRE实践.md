---
title: 阿里云 OSS 对象存储 SRE 实践
date: 2026-08-25 10:45:00
tags:
  - 阿里云
  - OSS
categories:
  - 阿里云资源 SRE
---

OSS 用于静态资源、备份、日志归档，SRE 需关注**权限、生命周期、跨 Region 容灾**。

## Bucket 规划

```
命名：{company}-{env}-{purpose}-{region}
例：acme-prod-backup-hz

权限：私有（默认）
存储类型：
  标准：热数据
  低频/归档：备份、日志
  冷归档：合规长期保留
```

## 访问控制

| 方式 | 场景 |
|------|------|
| RAM Policy | 应用 SDK 访问 |
| STS 临时凭证 | 前端直传 |
| Bucket Policy | 跨账号 |
| 禁止公共读 | 生产强制 |

```json
{
  "Version": "1",
  "Statement": [{
    "Effect": "Deny",
    "Principal": ["*"],
    "Action": ["oss:*"],
    "Resource": ["acs:oss:*:*:acme-prod-*/*"],
    "Condition": {
      "Bool": { "acs:SecureTransport": "false" }
    }
  }]
}
```

## 生命周期

```xml
<!-- 30 天转低频，90 天转归档，365 天删除 -->
<LifecycleConfiguration>
  <Rule>
    <Prefix>logs/</Prefix>
    <Status>Enabled</Status>
    <Transition><Days>30</Days><StorageClass>IA</StorageClass></Transition>
    <Transition><Days>90</Days><StorageClass>Archive</StorageClass></Transition>
    <Expiration><Days>365</Days></Expiration>
  </Rule>
</LifecycleConfiguration>
```

## 跨 Region 复制

```
源 Bucket cn-hangzhou → 目标 Bucket cn-shanghai（CRR）
用于灾备、合规
```

## 监控

| 指标 | 告警 |
|------|------|
| 存储量 | 预算阈值 |
| 请求 4xx/5xx | 突增 |
| 流量 | 异常 egress |

## 与 RDS 备份

RDS 备份可转储 OSS，异地 Bucket 存副本。

## Checklist

- [ ] 私有 Bucket + HTTPS
- [ ] 生命周期降本
- [ ] 版本控制（防误删，可选）
- [ ] 跨 Region 复制（灾备）
- [ ] RAM 最小权限

OSS **公共读 Bucket 是数据泄露高发区**。
