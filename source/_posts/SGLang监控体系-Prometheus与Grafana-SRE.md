---
title: SGLang 监控体系：Prometheus 与 Grafana
date: 2026-09-06 09:45:00
tags:
  - SGLang
  - SRE
  - 监控
categories:
  - SGLang SRE
---

没有指标就没有 SLA。SGLang 生产至少要覆盖 **请求、延迟、队列、缓存、GPU**。

## 指标分层

| 层 | 示例 |
|----|------|
| 业务/API | QPS、5xx、流式中断率 |
| 推理 | TTFT、TPOT、token/s、排队时长 |
| 缓存 | Radix/前缀命中率、缓存占用 |
| 资源 | GPU util、显存、CPU、网络 |
| 平台 | Pod 重启、节点 NotReady |

## 接入方式

```
SGLang /metrics → Prometheus scrape
               → Grafana Dashboard
               → Alertmanager
```

- ServiceMonitor / PodMonitor（K8s）  
- 静态 scrape（Docker / VM）  

## Grafana 面板建议

1. **总览**：可用性、QPS、错误率  
2. **延迟**：TTFT / 端到端 P50/P99  
3. **饱和**：队列深度、并发占用  
4. **缓存**：命中率趋势  
5. **GPU**：利用率与显存  

## SRE 实践

- 指标命名与标签统一：`model`、`instance`、`tp`  
- 保留足够 retention（建议 ≥15 天细粒度）  
- 面板与告警用同一 PromQL，避免「看板绿、告警红」

## 反模式

- 只看 GPU util，不看排队与 TTFT  
- 无 model 标签，多池无法定位  
- 结构化/长上下文流量与短 Chat 混在同一均值里解读

**先有可刮取的 /metrics，再谈调优。**
