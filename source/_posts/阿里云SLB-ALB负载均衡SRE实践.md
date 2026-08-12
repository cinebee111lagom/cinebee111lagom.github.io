---
title: 阿里云 SLB/ALB 负载均衡 SRE 实践
date: 2026-08-25 10:15:00
tags:
  - 阿里云
  - SLB
  - ALB
categories:
  - 阿里云资源 SRE
---

负载均衡是生产入口，SRE 需保障**多 AZ、健康检查、TLS 与可观测**。

## SLB vs ALB

| | CLB（传统 SLB） | ALB（应用型） |
|---|----------------|---------------|
| 层级 | 4/7 层 | 7 层为主 |
| 路由 | 基础 | 高级（Header、Path） |
| 推荐 | 遗留 | **新生产首选** |

## ALB 多 AZ 配置

```
ALB（公网/私网）
├── 监听 443 HTTPS（证书 ACM）
├── 服务器组（多 AZ ECS/ENI）
│   ├── cn-hangzhou-h: 2 实例
│   └── cn-hangzhou-i: 2 实例
└── 健康检查 GET /health 200
```

## 健康检查

| 参数 | 建议 |
|------|------|
| 路径 | /health 或 /ready |
| 间隔 | 2~5s |
| 不健康阈值 | 3 次 |
| 超时 | 2~3s |

应用 **liveness vs readiness** 分离（K8s 场景由 Ingress 接管）。

## HTTPS

- 证书：SSL 证书服务（免费/付费）
- 策略：TLS 1.2+，强 cipher
- HTTP → HTTPS 301 跳转

## 会话保持

```
有状态会话：启用 Cookie 粘性（谨慎）
无状态 API：关闭会话保持
```

## 监控告警

| 指标 | 告警 |
|------|------|
| UnhealthyHostCount | > 0 P1 |
| ActiveConnection | 突增/突降 |
| HTTPCode_5XX | > 1% P1 |

## 与 WAF 配合

```
用户 → WAF → ALB → 后端
```

DDoS 高防 + WAF 在 ALB 前。

## Checklist

- [ ] 后端跨至少 2 AZ
- [ ] 健康检查与真实业务一致
- [ ] 连接优雅退出（draining 30s）
- [ ] 访问日志投递 SLS

**单 AZ 后端 + 多 AZ LB ≠ 高可用**。
