---
title: 阿里云 SLB 与 ALB 负载均衡运维
date: 2026-08-26 10:00:00
tags:
  - 阿里云
  - SLB
  - ALB
categories:
  - 阿里云资源 SRE
---

负载均衡是流量入口，SRE 需保障高可用、健康检查与证书。

## SLB vs ALB

| | CLB（传统 SLB） | ALB（应用型） |
|---|----------------|---------------|
| 协议 | 4/7 层 | 7 层为主 |
| 路由 | 简单 | 高级（Header/Path） |
| 推荐 | 遗留 TCP | 新 Web/API |

## 高可用配置

```
实例：公网/私网
多 AZ 部署：每个 AZ 至少 1 后端 ECS/ENI
健康检查：
  HTTP GET /health → 200
  间隔 2s，不健康阈值 3
```

## 后端服务器组

```
权重：默认 100
慢启动：新实例 30s 渐增流量
会话保持：无状态 API 关闭；Web 可选 Cookie
```

## HTTPS 证书

```
证书：阿里云 SSL 证书服务 或 上传
TLS 1.2+，禁用弱 cipher
HTTP → HTTPS 强制跳转
证书到期前 30 天告警
```

## 与 ACK 集成

```
ALB Ingress Controller
  → 自动创建 ALB
  → 关联 Ingress 规则
```

## 监控告警

| 指标 | 告警 |
|------|------|
| UnhealthyServerCount | > 0 P1 |
| QPS 突降 | 50% P1 |
| RT P99 | > SLA P2 |

## Runbook：后端全红

```
1. 检查 ECS/容器 health endpoint
2. 安全组是否变更
3. 后端端口是否监听
4. 证书是否过期
5. 最近发布是否引入 bug
```

入口层高可用 = **多 AZ LB + 多 AZ 后端 + 有效健康检查**。
