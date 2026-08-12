---
title: 阿里云 CloudMonitor 与可观测体系
date: 2026-08-26 11:15:00
tags:
  - 阿里云
  - CloudMonitor
  - 监控
categories:
  - 阿里云资源 SRE
---

CloudMonitor 是阿里云统一监控入口，SRE 需建立**指标、日志、链路**三位一体。

## CloudMonitor 指标

```
云产品自动接入：ECS、RDS、SLB、OSS、Redis...
自定义：Agent 上报 或 Prometheus 远程写入
```

## 告警规则模板

```yaml
# 示例：ECS CPU
产品：ECS
指标：CPUUtilization
周期：1 分钟
条件：平均值 >= 80%，持续 3 周期
级别：P1
通知：钉钉/短信/on-call
```

## 应用分组

```
按标签自动分组：
  env=prod AND app=order
→ 批量应用告警模板
```

## 日志服务 SLS

```
ECS/ACK logtail → Logstore → 查询/告警/投递 OSS
结构化 JSON 日志
关联 request_id
```

## ARMS（应用监控）

```
Java/Python/Go Agent
  → 链路追踪
  → 应用拓扑
  → 异常分析
```

## Prometheus 集成

```
ACK 托管 Prometheus
  → 采集 Pod/自定义 metrics
  → Grafana 托管版
  → 告警 → 钉钉
```

## 可观测分层

| 层 | 工具 |
|----|------|
| 基础设施 | CloudMonitor |
| 容器 | ACK Prometheus |
| 应用 | ARMS |
| 日志 | SLS |
| 合成 | 云监控站点监控 |

## Checklist

- [ ] 核心资源告警模板 100% 覆盖
- [ ] 告警收敛（同一故障不轰炸）
- [ ] Runbook 链接在通知中
- [ ] 日志 30 天保留（合规）

**无告警=盲飞，告警太多=狼来了**，需季度 review。
