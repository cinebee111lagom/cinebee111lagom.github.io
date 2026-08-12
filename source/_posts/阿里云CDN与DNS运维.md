---
title: 阿里云 CDN 与 DNS 运维
date: 2026-08-25 12:45:00
tags:
  - 阿里云
  - CDN
  - DNS
categories:
  - 阿里云资源 SRE
---

**CDN** 加速静态资源，**云解析 DNS / GTM** 负责流量调度与容灾切换。

## CDN 架构

```
用户 → CDN 边缘节点 → 回源（OSS / SLB / 源站）
```

## 配置要点

| 项 | 建议 |
|----|------|
| 缓存规则 | 静态长缓存，HTML 短缓存 |
| HTTPS | 强制 HTTPS、HTTP/2 |
| 回源 Host | 与源站 SNI 一致 |
| 预热 | 大促前 URL 预热 |
| 刷新 | 发布时目录/URL 刷新 |

## 回源优化

```
OSS 回源：私有 Bucket + CDN 鉴权
SLB 回源：仅 CDN 回源 IP 白名单
```

## 云解析 DNS

```
A/AAAA/CNAME 记录
TTL：生产 60~300s（便于切换）
健康检查：HTTP/TCP 探测
```

## GTM（全局流量管理）

```
多 Region / 多 SLB 智能调度
故障转移：主不可用 → 备
权重：灰度、A/B
```

## 监控

| 指标 | 告警 |
|------|------|
| 回源 5xx | > 1% |
| 命中率 | < 85% 排查 |
| 带宽 | 突增（攻击/热点） |

## 故障 Runbook

```
1. CDN 502 → 查回源 SLB/OSS 健康
2. 全站不可达 → DNS 解析 + GTM 状态
3. 缓存污染 → 刷新 + 版本号 query
```

## Checklist

- [ ] HTTPS 全站
- [ ] 回源仅 CDN IP
- [ ] 大促预热清单
- [ ] GTM 健康检查
- [ ] DNS TTL 与切换演练

CDN/DNS 是**用户入口第一层**，与 WAF、SLB 联动。
