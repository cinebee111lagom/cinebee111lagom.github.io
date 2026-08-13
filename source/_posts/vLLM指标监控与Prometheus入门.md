---
title: vLLM 指标监控与 Prometheus 入门
date: 2026-09-03 12:30:00
tags:
  - vLLM
  - Prometheus
  - 入门
categories:
  - vLLM 新手入门
---

vLLM 暴露 **Prometheus metrics**，用于观察吞吐、延迟与缓存命中。

## 开启指标

较新版本默认提供 metrics 端点（路径以版本文档为准），常见：

```bash
curl http://localhost:8000/metrics | head
```

启动时可关注与观测相关的参数（如日志级别、统计开关）。

## 关键指标（名称随版本变化）

| 类型 | 关注点 |
|------|--------|
| 请求数 | QPS、成功/失败 |
| 延迟 | TTFT、端到端 latency |
| Token | prompt/generation tokens 速率 |
| 缓存 | KV / prefix cache 命中 |
| 调度 | 排队请求数、running |

## Grafana

- 面板：TTFT、TPOT、GPU 利用率、队列长度
- 配合 `dcgm-exporter` / `nvidia-smi` 看显存与温度

## 告警起步

```yaml
- alert: VllmHighLatency
  expr: histogram_quantile(0.99, rate(vllm_request_latency_seconds_bucket[5m])) > 10
  for: 10m

- alert: VllmServiceDown
  expr: up{job="vllm"} == 0
  for: 2m
```

具体 metric 名请对照你安装版本的 `/metrics`。

## 反模式

- 只看 GPU util 不看排队与 TTFT
- 无健康检查仅依赖业务报错
- 压测时不开 metrics

下一篇：**性能调优入门**。
