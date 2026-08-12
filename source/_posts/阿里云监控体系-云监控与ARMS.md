---
title: 阿里云监控体系：云监控与 ARMS
date: 2026-08-25 11:00:00
tags:
  - 阿里云
  - 监控
categories:
  - 阿里云资源 SRE
---

阿里云可观测由**云监控**（基础设施）+ **ARMS**（应用）+ **SLS**（日志）组成。

## 云监控（CloudMonitor）

```
ECS/RDS/SLB/OSS 等 → 默认指标
                  → 告警规则 → 短信/钉钉/飞书
                  → Dashboard
```

## 关键指标（ECS）

| 指标 | 告警 |
|------|------|
| CPUUtilization | > 85% 持续 |
| memory_usedutilization | > 90% |
| diskusage_utilization | > 85% |
| StatusCheck | 失败 P0 |

## 自定义监控

```bash
# 安装云监控 agent 上报进程/端口
# 或使用 Prometheus 托管服务 ARMS Prometheus
```

## ARMS 应用监控

- Java/Go/Python 探针
- 分布式链路追踪
- 与 ECS/ACK 集成

## SLS 日志

```
ALB 访问日志 → Logstore
ActionTrail → 审计
应用 JSON 日志 → 查询 + 告警（Scheduled SQL）
```

## Prometheus 集成

```
ACK 集群 → ARMS Prometheus 或自建
dcgm-exporter / mysql_exporter → 远程写入
Grafana 对接 ARMS 或自建
```

## 告警分级

| 级别 | 通道 |
|------|------|
| P0 | 电话 + 短信 + 钉钉 |
| P1 | 短信 + 钉钉 |
| P2 | 钉钉 |
| P3 | 邮件 |

## Checklist

- [ ] 核心产品告警全覆盖
- [ ] 告警收敛（同一故障不轰炸）
- [ ] Dashboard 按 env/project
- [ ] 日志与指标关联 trace_id
- [ ] Runbook 链接在告警模板

**没有告警的云资源 = 盲飞**。
