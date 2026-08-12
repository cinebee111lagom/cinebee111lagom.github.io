---
title: 阿里云 OSS 对象存储 SRE 实践
date: 2026-08-26 10:45:00
tags:
  - 阿里云
  - OSS
categories:
  - 阿里云资源 SRE
---

OSS 用于静态资源、备份、日志归档，SRE 需关注权限、生命周期与跨域复制。

## Bucket 规划

```
命名：company-{env}-{purpose}
例：company-prod-static
     company-prod-backup
     company-log-archive

地域：与计算同 Region 降延迟和流量费
```

## 权限模型

```
禁止 Bucket 公共读写
RAM Policy 最小权限
STS 临时凭证给前端直传
```

```json
{
  "Version": "1",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["oss:GetObject", "oss:PutObject"],
    "Resource": ["acs:oss:*:*:company-prod-static/app/*"]
  }]
}
```

## 生命周期

```
30 天 → 标准
90 天 → 低频 IA
365 天 → 归档 / 冷归档
日志 Bucket：7 天转 IA，90 天删除
```

## 版本控制与回收站

- 核心 Bucket 开启**版本控制**
- 开启**回收站**防误删

## 跨地域复制（DR）

```
源 Bucket（杭州）→ CRR → 目标 Bucket（深圳）
RPO：分钟级（异步复制）
```

## 监控

| 指标 | 告警 |
|------|------|
| 存储量突增 | 50% P2 |
| 4xx/5xx 请求比 | 升高 P1 |
| 流量费用异常 | FinOps 告警 |

## 最佳实践

- 大文件用分片上传
- CDN 加速静态资源（源站 OSS）
- 服务端加密 SSE-OSS 或 KMS

OSS 成本低但**权限误配**是常见安全事故源。
