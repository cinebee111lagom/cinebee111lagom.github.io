---
title: SGLang 监控与 Prometheus 入门
date: 2026-09-05 12:15:00
tags:
  - SGLang
  - Prometheus
  - 入门
categories:
  - SGLang 新手入门
---

生产需观察 **延迟、吞吐、缓存命中、GPU**。

## 指标端点

SGLang 通常暴露 Prometheus 指标（路径以版本文档为准），例如：

```bash
curl http://localhost:30000/metrics | head
```

## 关注点

| 类型 | 说明 |
|------|------|
| 请求量 | QPS、成功/失败 |
| 延迟 | TTFT、端到端 |
| 缓存 | Radix/前缀命中 |
| 队列 | 等待与运行中请求 |
| Token | 输入/输出速率 |

同时抓取 **DCGM / nvidia-smi** 看显存与温度。

## Grafana

- 面板：TTFT P99、token/s、命中率、GPU util  
- 按 model/instance 分面  

## 告警起步

```yaml
- alert: SGLangDown
  expr: up{job="sglang"} == 0
  for: 2m

- alert: SGLangHighLatency
  expr: histogram_quantile(0.99, rate(sglang_request_latency_seconds_bucket[5m])) > 10
  for: 10m
```

指标名请对照实际 `/metrics`。

## 反模式

- 只看容器 Alive 不看排队
- 无 GPU 指标
- 压测时不开监控

下一篇：**性能调优**。
