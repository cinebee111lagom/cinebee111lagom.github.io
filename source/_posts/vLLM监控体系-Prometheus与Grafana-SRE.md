---
title: vLLM 监控体系：Prometheus 与 Grafana
date: 2026-09-04 10:00:00
tags:
  - vLLM
  - SRE
  - Prometheus
categories:
  - vLLM SRE
---

推理 SRE 至少盯：**可用性、延迟、队列、GPU、Token 速率**。

## 采集

```yaml
scrape_configs:
  - job_name: vllm
    metrics_path: /metrics
    static_configs:
      - targets: ["vllm-chat:8000", "vllm-coder:8000"]
        labels:
          pool: llm
```

同时采集：

- `dcgm-exporter` / `nvidia-smi`（GPU）
- node_exporter（CPU/磁盘，模型加载 IO）
- 网关 QPS/5xx

## 核心 SLI

| SLI | 说明 |
|-----|------|
| 可用性 | up + /health |
| TTFT | 首 token 延迟 |
| E2E latency | 端到端 |
| Queue depth | 排队请求 |
| Token/s | 输入/输出吞吐 |
| GPU util / 显存 | 饱和与 OOM 风险 |

> 指标名随 vLLM 版本变化，以实例 `/metrics` 为准。

## Grafana 面板建议

1. 请求 QPS / 错误率  
2. TTFT P50/P99  
3. 运行中/等待中请求数  
4. GPU 利用率、显存  
5. 按 model 分面  

## 日志

- 结构化访问日志（request_id、model、tokens、latency）
- OOM、NCCL、权重加载失败进 ERROR 告警

## 反模式

- 只监控容器 up，不监控排队
- 无 GPU 指标，OOM 后才发现
- 多实例无 `instance`/`model` 标签

监控门禁：**无 metrics 不上线**。
